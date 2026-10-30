import numpy as np
import pandas as pd

from tfexflow.backtest.engine import run, size_contracts, walk_forward
from tfexflow.config import DEFAULT, Settings
from tfexflow.data import synthetic
from tfexflow.data.loaders import load
from tfexflow.features import build_features


def _frame(n=6, base=1000.0):
    idx = pd.bdate_range("2025-01-06", periods=n)
    close = base + np.arange(n) * 2.0          # ขึ้นวันละ 2 จุด
    return pd.DataFrame({"open": close - 1, "high": close + 3, "low": close - 3, "close": close,
                         "volume": 1.0, "open_interest": 1.0, "atr": 5.0}, index=idx)


def test_กำไรขาดทุนคำนวณตรงกับมือ_รวมต้นทุนสองข้าง():
    st = DEFAULT
    f = _frame()
    state = pd.Series([1, 1, 1, 0, 0, 0], index=f.index)  # สัญญาณวัน0 → เข้า open วัน1 · สัญญาณ FLAT วัน3 → ออก open วัน4
    r = run(f, st, state=state)
    k = size_contracts(5.0, st)
    assert k == 5                                      # 10,000 ÷ (2×5×200) = 5
    t = r.trades.iloc[0]
    assert t["entry"] == f["open"].iloc[1] and t["exit"] == f["open"].iloc[4]
    assert t["points"] == 6.0
    expected = 6.0 * 200 * k - st.cost.round_trip_thb() * k
    assert abs(t["pnl_net"] - expected) < 1e-6
    assert abs(r.daily["pnl_net"].sum() - expected) < 1e-6


def test_ไม่มองอนาคต_สัญญาณวันนี้ไม่ได้เทรดราคาวันนี้():
    f = _frame()
    state = pd.Series([0, 0, 0, 0, 0, 1], index=f.index)  # สัญญาณมาวันสุดท้าย → ไม่มีวันถัดไปให้เข้า
    r = run(f, DEFAULT, state=state)
    assert r.trades.empty and r.daily["contracts"].sum() == 0


def test_stop_ทำงานเมื่อราคาแตะ():
    f = _frame()
    f.loc[f.index[2], "low"] = 900.0            # วันที่ 2 ราคาร่วงทะลุ stop
    state = pd.Series([1, 1, 1, 1, 1, 1], index=f.index)
    r = run(f, DEFAULT, state=state)
    first = r.trades.iloc[0]
    assert first["reason"] == "stop" and abs(first["points"] + 10.0) < 1e-9   # 2 ATR = 10 จุด


def test_สวิตช์ตัด_หยุดเทรดหลังขาดทุนเกินกำหนด():
    from dataclasses import replace
    st = replace(DEFAULT, risk=replace(DEFAULT.risk, max_drawdown_pct=0.001, cooldown_days=3))
    f = _frame(10)
    f["close"] = 1000 - np.arange(10) * 20.0; f["open"] = f["close"] + 10; f["high"] = f["open"] + 1; f["low"] = f["close"] - 1
    state = pd.Series(1, index=f.index)
    r = run(f, st, state=state)
    assert r.summary["kill_switch_triggers"] >= 1
    killed_day = r.daily.index[r.daily["killed"]][0]
    after = r.daily.loc[killed_day:].iloc[1:4]
    assert (after["contracts"] == 0).all()


def test_ข้อมูลไม่มีสัญญาณ_กำไรก่อนต้นทุนเฉลี่ยใกล้ศูนย์(tmp_path):
    """สมมุติฐานว่าง: ถ้าไม่มีผลของกระแสเงินในข้อมูล ระบบต้องไม่ "หาเงินจากอากาศ"

    หนึ่ง seed มี σ ราว 30,000 ฿ (วัดจาก 30 seeds · ค่าเฉลี่ย −2,780 · t = −0.5) จึงใช้ค่าเฉลี่ย 6 seeds
    และขอบเขต 2.5σ/√6 ≈ 31,000 ฿ — ถ้าเทสต์นี้แดง แปลว่าเครื่องทดสอบมีอคติเชิงระบบ ไม่ใช่โชคร้าย
    """
    grosses = []
    for seed in (21, 22, 23, 24, 25, 26):
        folder = synthetic.write(tmp_path / f"null{seed}", years=3, seed=seed, flow_effect=0.0)
        feats = build_features(load(folder), DEFAULT.features)
        r = run(feats, DEFAULT)
        grosses.append(r.daily["pnl_gross"].sum())
        assert r.summary["total_cost_thb"] > 0
    assert abs(np.mean(grosses)) < 31_000


def test_walk_forward_ให้ผลเฉพาะช่วงทดสอบ(feats):
    wf = walk_forward(feats, DEFAULT, train_days=245, test_days=61)
    assert len(wf["folds"]) >= 5
    assert wf["oos_daily"].index[0] == feats.index[245]
    assert set(wf["folds"]["threshold"]) <= {0.15, 0.2, 0.3, 0.4, 0.5}
