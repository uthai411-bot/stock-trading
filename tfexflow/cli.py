"""คำสั่งบรรทัดเดียวสำหรับทุกขั้น — ทุกคำสั่งอ่านข้อมูลจาก --data และเขียนผลลง --out"""
import argparse
import json
from pathlib import Path

import pandas as pd

from .config import DEFAULT, Settings
from .data import synthetic
from .data.loaders import load
from .features import build_features
from .signals.composite import composite_score, state_label, to_state


def _is_synthetic(folder: Path) -> bool:
    return (folder / "SYNTHETIC.txt").exists()


def _prepare(folder: str, st: Settings):
    ds = load(folder)
    feats = build_features(ds, st.features)
    score, used = composite_score(feats, st.weights)
    state = to_state(score, feats.get("trend"), st.rules)
    return ds, feats, score, state, used


def cmd_synth(a):
    out = synthetic.write(a.out, years=a.years, seed=a.seed, flow_effect=a.flow_effect)
    print(f"สร้างข้อมูลจำลอง {a.years} ปี ไว้ที่ {out.resolve()} (flow_effect={a.flow_effect})")


def cmd_hypothesis(a):
    from .research.hypothesis import evaluate, verdict
    st = DEFAULT
    _, feats, score, _, _ = _prepare(a.data, st)
    feats = feats.assign(score=score)
    table = evaluate(feats, cost=st.cost, spec=st.spec)
    v = verdict(table)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    table.to_csv(Path(a.out) / "hypothesis_full.csv", index=False)
    v.to_csv(Path(a.out) / "hypothesis_verdict.csv", index=False)
    pd.set_option("display.width", 160); pd.set_option("display.max_columns", 20)
    print(f"ต้นทุนไปกลับ {st.cost.round_trip_points(st.spec):.2f} จุด/สัญญา\n")
    print(v[["factor", "horizon", "n", "ic", "t_stat", "hit_rate", "spread", "spread_after_cost", "verdict"]]
          .to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    if _is_synthetic(Path(a.data)):
        print("\n★ ข้อมูลจำลอง — ผลนี้ใช้ตรวจว่าโปรแกรมทำงาน ไม่ใช่หลักฐานเรื่องตลาดจริง")


def cmd_backtest(a):
    from .backtest.engine import run, walk_forward
    st = DEFAULT
    _, feats, _, _, _ = _prepare(a.data, st)
    r = run(feats, st)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    r.daily.to_csv(Path(a.out) / "backtest_daily.csv")
    r.trades.to_csv(Path(a.out) / "backtest_trades.csv", index=False)
    print("น้ำหนักที่ใช้จริง:", {k: round(v, 3) for k, v in r.weights_used.items()})
    print("\n== ทั้งช่วง (in-sample · พารามิเตอร์เริ่มต้น) ==")
    for k, v in r.summary.items():
        print(f"  {k:<22} {v:,.2f}" if isinstance(v, float) else f"  {k:<22} {v}")
    if not a.no_wf:
        wf = walk_forward(feats, st)
        wf["folds"].to_csv(Path(a.out) / "walkforward_folds.csv", index=False)
        print("\n== walk-forward (out-of-sample เท่านั้น) ==")
        if wf["oos_summary"]:
            for k in ("days", "total_pnl_thb", "sharpe", "max_drawdown_pct", "profit_factor", "kill_switch_triggers"):
                v = wf["oos_summary"][k]
                print(f"  {k:<22} {v:,.2f}" if isinstance(v, float) else f"  {k:<22} {v}")
            print(wf["folds"].to_string(index=False))
        else:
            print("  ข้อมูลสั้นเกินกว่าจะทำ walk-forward (ต้องมากกว่า 306 วันทำการ)")
    if _is_synthetic(Path(a.data)):
        print("\n★ ข้อมูลจำลอง — ผลนี้ไม่มีความหมายต่อการลงทุนจริง")


def cmd_signal(a):
    st = DEFAULT
    _, feats, score, state, used = _prepare(a.data, st)
    last = feats.index[-1]
    from .backtest.engine import size_contracts
    atr = float(feats["atr"].iloc[-1])
    payload = {
        "as_of": str(last.date()),
        "applies_to": "ราคาเปิดวันทำการถัดไป",
        "state": state_label(int(state.iloc[-1])),
        "score": round(float(score.iloc[-1]), 4),
        "close": float(feats["close"].iloc[-1]),
        "ema_slow": round(float(feats["ema_slow"].iloc[-1]), 2),
        "atr": round(atr, 2),
        "suggested_contracts": size_contracts(atr, st),
        "stop_distance_points": round(st.risk.atr_stop_multiple * atr, 1),
        "factors": {k: {"weight": round(w, 3), "value": round(float(feats[f"f_{k}"].iloc[-1]), 4)}
                    for k, w in used.items()},
        "synthetic": _is_synthetic(Path(a.data)),
    }
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "signal.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_report(a):
    from .backtest.engine import run
    from .report.html import render
    from .research.hypothesis import evaluate, verdict
    st = DEFAULT
    ds, feats, score, state, used = _prepare(a.data, st)
    r = run(feats, st)
    feats = feats.join(r.daily[["equity"]])
    hyp = verdict(evaluate(feats.assign(score=score), cost=st.cost, spec=st.spec))
    html = render(feats, score, state, used, r.summary, hyp, ds.source, synthetic=_is_synthetic(Path(a.data)))
    Path(a.out).mkdir(parents=True, exist_ok=True)
    p = Path(a.out) / "report.html"
    p.write_text(html, encoding="utf-8")
    print(f"เขียนแดชบอร์ดที่ {p.resolve()}")


def cmd_roll(a):
    from .ingest.roll import build_continuous, read_series_dir, write_s50_daily
    frames = read_series_dir(a.series_dir)
    cont = build_continuous(frames)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    write_s50_daily(cont, Path(a.out) / "s50_daily.csv")
    rolls = cont["series"].ne(cont["series"].shift()).sum() - 1
    print(f"ต่อ {len(frames)} ซีรีส์ → {len(cont)} วัน · roll {rolls} ครั้ง · เขียน {Path(a.out) / 's50_daily.csv'}")
    print(f"ช่วง {cont.index[0].date()} ถึง {cont.index[-1].date()} · ซีรีส์ล่าสุด {cont['series'].iloc[-1]}")


def cmd_fetch(a):
    from .ingest import series as SR
    from .ingest.envfile import load_env
    from .ingest.settrade import fetch_daily, market_from_env
    load_env(a.env)
    market = market_from_env()
    sdir = Path(a.out) / "series"; sdir.mkdir(parents=True, exist_ok=True)
    codes = SR.series_between(a.start, a.end)
    got = 0
    for code in codes:
        df = fetch_daily(market, code, a.start, a.end)
        if df.empty:
            continue
        df = df.assign(open_interest=float("nan"))
        df.index = df.index.strftime("%Y-%m-%d"); df.index.name = "date"
        df.to_csv(sdir / f"{code}.csv"); got += 1
        print(f"  {code}: {len(df)} วัน")
    idx = fetch_daily(market, "SET50", a.start, a.end)[["close"]]
    idx.index = idx.index.strftime("%Y-%m-%d"); idx.index.name = "date"
    idx.to_csv(Path(a.out) / "set50_index_daily.csv")
    print(f"ดึง {got} ซีรีส์ + ดัชนี SET50 {len(idx)} วัน · ต่อเป็นเส้นเดียวด้วย: "
          f"python3 -m tfexflow roll --series-dir {sdir} --out {a.out}")


def _pairs(text: str) -> tuple[float, float]:
    b, s = text.split("/")
    return float(b.replace(",", "")), float(s.replace(",", ""))


def cmd_add_flow(a):
    from .ingest.flowlog import SET_TYPES, TFEX_TYPES, append
    types = SET_TYPES if a.market == "set" else TFEX_TYPES
    values = {t: _pairs(getattr(a, t)) for t in types if getattr(a, t, None)}
    p = append(a.data, a.market, a.date, values)
    print(f"บันทึก {a.market.upper()} วันที่ {a.date} ลง {p}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tfexflow", description="กระแสเงินรายกลุ่ม + วอลุ่ม SET50 → สัญญาณ S50")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("synth", help="สร้างข้อมูลจำลอง"); s.set_defaults(fn=cmd_synth)
    s.add_argument("--out", default="data/sample"); s.add_argument("--years", type=int, default=3)
    s.add_argument("--seed", type=int, default=7); s.add_argument("--flow-effect", type=float, default=0.0015)

    for name, fn, help_ in (("hypothesis", cmd_hypothesis, "วัดอำนาจทำนาย"), ("backtest", cmd_backtest, "ทดสอบย้อนหลัง"),
                            ("signal", cmd_signal, "สัญญาณวันถัดไป"), ("report", cmd_report, "แดชบอร์ด HTML")):
        s = sub.add_parser(name, help=help_); s.set_defaults(fn=fn)
        s.add_argument("--data", required=True); s.add_argument("--out", default="out")
        if name == "backtest":
            s.add_argument("--no-wf", action="store_true", help="ข้าม walk-forward")
    s = sub.add_parser("roll", help="ต่อไฟล์รายซีรีส์ (S50Z26.csv …) เป็น s50_daily.csv"); s.set_defaults(fn=cmd_roll)
    s.add_argument("--series-dir", required=True); s.add_argument("--out", required=True)

    s = sub.add_parser("fetch", help="ดึงแท่งเทียนรายวันจาก Settrade Open API (อ่านอย่างเดียว)"); s.set_defaults(fn=cmd_fetch)
    s.add_argument("--start", required=True); s.add_argument("--end", required=True)
    s.add_argument("--out", default="data/real"); s.add_argument("--env", default=".env")

    s = sub.add_parser("add-flow", help="กรอกยอดซื้อ/ขายรายกลุ่มของวันเดียว (ซื้อ/ขาย เช่น 30500/33363)")
    s.set_defaults(fn=cmd_add_flow)
    s.add_argument("market", choices=["set", "tfex"]); s.add_argument("--date", required=True)
    s.add_argument("--data", default="data/real")
    for t in ("foreign", "institution", "proprietary", "retail", "local"):
        s.add_argument(f"--{t}", help=f"{t}: ซื้อ/ขาย")

    a = ap.parse_args(argv)
    a.fn(a)
    return 0
