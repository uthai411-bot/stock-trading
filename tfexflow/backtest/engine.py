"""ทดสอบย้อนหลังรายวัน — ตรงไปตรงมา ไม่มีเวทมนตร์ ทุกบรรทัดอ่านแล้วอธิบายให้ผู้ทำบัญชีฟังได้

ลำดับเวลาในหนึ่งวัน t:
  1. เปิดตลาด: ปรับสถานะให้ตรงกับ state ของ "เมื่อวาน" (t−1) ที่ราคา open(t) — ไม่ใช่ state ของวันนี้
  2. ระหว่างวัน: ถ้าราคาแตะ stop (entry ∓ k·ATR) ถือว่าออกที่ stop
  3. ปิดตลาด: mark-to-market ที่ close(t) · ตรวจขาดทุนรายวันและสวิตช์ตัด
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import Settings
from ..signals.composite import FLAT, LONG, SHORT, composite_score, to_state
from .metrics import summarize


@dataclass
class BacktestResult:
    daily: pd.DataFrame
    trades: pd.DataFrame
    summary: dict
    weights_used: dict[str, float] = field(default_factory=dict)


def size_contracts(atr: float, st: Settings) -> int:
    """จำนวนสัญญาจากความเสี่ยงต่อรอบ: ทุน × %เสี่ยง ÷ (ระยะ stop เป็นจุด × 200)"""
    if not np.isfinite(atr) or atr <= 0:
        return 0
    risk_thb = st.risk.capital_thb * st.risk.risk_per_trade_pct
    per_contract = st.risk.atr_stop_multiple * atr * st.spec.point_value_thb
    return int(min(st.risk.max_contracts, max(0, risk_thb // per_contract)))


def run(feats: pd.DataFrame, st: Settings, state: pd.Series | None = None) -> BacktestResult:
    weights_used: dict[str, float] = {}
    if state is None:
        score, weights_used = composite_score(feats, st.weights)
        state = to_state(score, feats.get("trend"), st.rules)
    state = state.reindex(feats.index).fillna(0).astype(int)

    pv = st.spec.point_value_thb
    side_cost = st.cost.per_side_thb(st.spec)
    opens, highs, lows, closes = (feats[c].to_numpy() for c in ("open", "high", "low", "close"))
    atrs = feats["atr"].to_numpy() if "atr" in feats else np.full(len(feats), np.nan)
    n = len(feats)

    pos = 0; contracts = 0; entry = np.nan; stop = np.nan; entry_i = -1
    prev_close = np.nan
    equity = st.risk.capital_thb; peak = equity; cooldown = 0
    rows = []; trades = []

    def close_trade(i, price, reason):
        nonlocal pos, contracts, entry, stop, entry_i
        gross = (price - entry) * pos * contracts * pv
        cost = contracts * side_cost
        trades.append({"entry_date": feats.index[entry_i], "exit_date": feats.index[i],
                       "side": "LONG" if pos == LONG else "SHORT", "contracts": contracts,
                       "entry": entry, "exit": price, "points": (price - entry) * pos,
                       "pnl_gross": gross, "cost": cost + contracts * side_cost,  # รวมขาเข้า
                       "pnl_net": gross - cost - contracts * side_cost,
                       "hold_days": i - entry_i, "reason": reason})
        pos = FLAT; contracts = 0; entry = np.nan; stop = np.nan; entry_i = -1
        return cost

    for i in range(n):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        day_pnl = 0.0; day_cost = 0.0; killed = False
        target = int(state.iloc[i - 1]) if i > 0 else FLAT
        if cooldown > 0:
            target = FLAT; cooldown -= 1

        # 1. เปิดตลาด — ปรับสถานะ
        if pos != FLAT and target != pos:
            day_pnl += (o - prev_close) * pos * contracts * pv   # mark จาก close เมื่อวานถึงราคาออก
            day_cost += close_trade(i, o, "signal")
        if pos == FLAT and target != FLAT:
            k = size_contracts(atrs[i - 1] if i > 0 else np.nan, st)
            if k > 0:
                pos = target; contracts = k; entry = o; entry_i = i
                stop = o - target * st.risk.atr_stop_multiple * atrs[i - 1]
                day_cost += k * side_cost
                prev_close = o

        # 2. ระหว่างวัน — stop
        if pos != FLAT:
            hit = (pos == LONG and l <= stop) or (pos == SHORT and h >= stop)
            if hit:
                day_pnl += (stop - prev_close) * pos * contracts * pv
                day_cost += close_trade(i, stop, "stop")
            else:
                day_pnl += (c - prev_close) * pos * contracts * pv

        # 3. ปิดตลาด — ความเสี่ยง
        net = day_pnl - day_cost
        if pos != FLAT and net < -st.risk.daily_loss_limit_pct * st.risk.capital_thb:
            day_cost += close_trade(i, c, "daily_limit"); net = day_pnl - day_cost
        equity += net; peak = max(peak, equity)
        if peak - equity > st.risk.max_drawdown_pct * st.risk.capital_thb and cooldown == 0:
            if pos != FLAT:
                day_cost += close_trade(i, c, "kill_switch"); net = day_pnl - day_cost
            killed = True; cooldown = st.risk.cooldown_days; peak = equity

        prev_close = c
        rows.append({"date": feats.index[i], "state": int(state.iloc[i]), "position": pos,
                     "contracts": contracts, "pnl_gross": day_pnl, "cost": day_cost, "pnl_net": net,
                     "equity": equity, "killed": killed})

    daily = pd.DataFrame(rows).set_index("date")
    tr = pd.DataFrame(trades)
    return BacktestResult(daily, tr, summarize(daily, tr, st.risk.capital_thb, st.spec.trading_days_per_year),
                          weights_used)


# ───────────────────────── walk-forward ─────────────────────────

def _with_rules(st: Settings, **kw) -> Settings:
    from dataclasses import replace
    return replace(st, rules=replace(st.rules, **kw))


def walk_forward(feats: pd.DataFrame, st: Settings, train_days: int = 245, test_days: int = 61,
                 thresholds=(0.15, 0.2, 0.3, 0.4, 0.5), hold_days=(1, 3, 5)) -> dict:
    """เลือก (threshold, min_hold) จากช่วงฝึกด้วย Sharpe แล้วใช้กับช่วงทดสอบถัดไป · เลื่อนหน้าต่างไปเรื่อย

    ผลที่ควรดูคือ "oos" (out-of-sample) เท่านั้น · ถ้า oos ต่างจาก train มาก = overfit
    """
    folds = []; oos_daily = []
    start = 0
    while start + train_days + test_days <= len(feats):
        train = feats.iloc[start:start + train_days]
        test = feats.iloc[start + train_days:start + train_days + test_days]
        best = None
        for th in thresholds:
            for hd in hold_days:
                cand = _with_rules(st, long_threshold=th, short_threshold=-th, min_hold_days=hd)
                r = run(train, cand)
                key = (r.summary["sharpe"], r.summary["total_pnl_thb"])
                if best is None or key > best[0]:
                    best = (key, th, hd)
        _, th, hd = best
        chosen = _with_rules(st, long_threshold=th, short_threshold=-th, min_hold_days=hd)
        # ★ ให้ช่วงทดสอบเห็นปัจจัยที่ต้องการประวัติ (z-score) — ใช้ feats ทั้งก้อน แต่เริ่มนับผลจากวันแรกของ test
        r = run(feats.iloc[:start + train_days + test_days], chosen)
        seg = r.daily.loc[test.index[0]:]
        folds.append({"train_start": train.index[0].date(), "test_start": test.index[0].date(),
                      "test_end": test.index[-1].date(), "threshold": th, "min_hold": hd,
                      "train_sharpe": best[0][0], "oos_pnl_thb": float(seg["pnl_net"].sum())})
        oos_daily.append(seg)
        start += test_days
    if not oos_daily:
        return {"folds": pd.DataFrame(), "oos_daily": pd.DataFrame(), "oos_summary": {}}
    oos = pd.concat(oos_daily)
    oos["equity"] = st.risk.capital_thb + oos["pnl_net"].cumsum()
    fake_trades = pd.DataFrame({"pnl_net": oos.loc[oos["pnl_net"] != 0, "pnl_net"], "hold_days": 1})
    return {"folds": pd.DataFrame(folds), "oos_daily": oos,
            "oos_summary": summarize(oos, fake_trades, st.risk.capital_thb, st.spec.trading_days_per_year)}
