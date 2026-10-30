"""★ ข้อมูลจำลองสำหรับพัฒนาและทดสอบโปรแกรม — ไม่ใช่ข้อมูลตลาดจริง

ออกแบบให้มี "ผลของกระแสเงินต่างชาติ" ฝังอยู่เล็กน้อยและรู้ขนาดแน่นอน (`flow_effect`)
เพื่อให้เทสต์ตรวจได้ว่า `hypothesis` ตรวจพบผลที่ฝังไว้จริง และ backtest ไม่มองอนาคต
ถ้าตั้ง flow_effect=0 ผลทดสอบย้อนหลังต้องออกมาใกล้ศูนย์ลบต้นทุน — นั่นคือเทสต์ที่สำคัญที่สุด
"""
from pathlib import Path

import numpy as np
import pandas as pd

SYMBOLS = [f"STK{i:02d}" for i in range(1, 51)]


def make(years: int = 3, seed: int = 7, flow_effect: float = 0.0015,
         start: str = "2023-01-02") -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    n = int(years * 245)
    dates = pd.bdate_range(start, periods=n)

    # กระแสเงินต่างชาติ: AR(1) ให้มีความต่อเนื่องเหมือนของจริง (ล้านบาท)
    foreign = np.zeros(n)
    for t in range(1, n):
        foreign[t] = 0.35 * foreign[t - 1] + rng.normal(0, 2500)
    institution = rng.normal(0, 1500, n) - 0.2 * foreign
    proprietary = rng.normal(0, 800, n)
    retail = -(foreign + institution + proprietary)  # ยอดสุทธิทุกกลุ่มรวมเป็นศูนย์เหมือนของจริง

    # ผลตอบแทนดัชนี: สัญญาณจากกระแสเงินของ "เมื่อวาน" (ไม่ใช่วันนี้) + เสียงรบกวน
    noise = rng.normal(0, 0.009, n)
    f_std = foreign.std()
    ret = np.zeros(n)
    for t in range(1, n):
        ret[t] = flow_effect * (foreign[t - 1] / f_std) + noise[t]
    index_close = 900 * np.exp(np.cumsum(ret))

    # futures = index + basis ที่แกว่งรอบมูลค่ายุติธรรมเล็กน้อย
    basis = 2.0 + np.cumsum(rng.normal(0, 0.3, n)) * 0.1
    close = index_close + basis
    gap = rng.normal(0, 0.003, n)
    open_ = np.r_[close[0], close[:-1]] * (1 + gap)
    rng_hl = np.abs(rng.normal(0, 0.005, n))
    high = np.maximum(open_, close) * (1 + rng_hl)
    low = np.minimum(open_, close) * (1 - rng_hl)
    volume = rng.integers(80_000, 250_000, n).astype(float)
    oi = (300_000 + np.cumsum(rng.normal(0, 3000, n))).clip(150_000)

    s50 = pd.DataFrame({"date": dates, "open": open_.round(1), "high": high.round(1), "low": low.round(1),
                        "close": close.round(1), "volume": volume, "open_interest": oi.round(0)})
    index = pd.DataFrame({"date": dates, "close": index_close.round(2)})

    def inv_rows(net: np.ndarray, typ: str, scale: float):
        gross = np.abs(rng.normal(scale, scale * 0.2, n))
        return pd.DataFrame({"date": dates, "investor_type": typ,
                             "buy_value": (gross + net / 2).round(2),
                             "sell_value": (gross - net / 2).round(2)})
    set_inv = pd.concat([inv_rows(foreign, "foreign", 30_000), inv_rows(institution, "institution", 8_000),
                         inv_rows(proprietary, "proprietary", 6_000), inv_rows(retail, "retail", 25_000)])

    # TFEX: ต่างชาติใน futures เดินตามต่างชาติในหุ้นแบบหลวม ๆ
    tf_foreign = (foreign / 50 + rng.normal(0, 40, n))
    tf_inst = rng.normal(0, 25, n)
    tf_local = -(tf_foreign + tf_inst)

    def tf_rows(net, typ, scale):
        gross = np.abs(rng.normal(scale, scale * 0.2, n))
        return pd.DataFrame({"date": dates, "investor_type": typ,
                             "long_contracts": (gross + net / 2).round(0),
                             "short_contracts": (gross - net / 2).round(0)})
    tfex_inv = pd.concat([tf_rows(tf_foreign, "foreign", 60_000), tf_rows(tf_inst, "institution", 20_000),
                          tf_rows(tf_local, "local", 90_000)])

    # หุ้น 50 ตัว: เบต้าต่อดัชนี + เสียงรบกวนรายตัว · น้ำหนักลดหลั่นเหมือนของจริง (ตัวแรกหนักสุด)
    w = np.array([0.5 ** (i / 8) for i in range(50)]); w /= w.sum()
    beta = rng.uniform(0.6, 1.4, 50)
    stk_ret = ret[:, None] * beta[None, :] + rng.normal(0, 0.012, (n, 50))
    stk_close = 50 * np.exp(np.cumsum(stk_ret, axis=0))
    stk_vol = rng.integers(1_000_000, 20_000_000, (n, 50)).astype(float)
    cons = pd.DataFrame({
        "date": np.repeat(dates, 50), "symbol": np.tile(SYMBOLS, n),
        "close": stk_close.round(2).ravel(), "volume": stk_vol.ravel(),
        "weight": np.tile(w.round(5), n),
    })
    return {"s50_daily": s50, "set50_index_daily": index, "set_investor_daily": set_inv,
            "tfex_investor_daily": tfex_inv, "constituents_daily": cons}


def write(folder: str | Path, **kw) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name, df in make(**kw).items():
        df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_csv(folder / f"{name}.csv", index=False)
    (folder / "SYNTHETIC.txt").write_text(
        "ข้อมูลในโฟลเดอร์นี้เป็นข้อมูลจำลองที่สร้างด้วย tfexflow synth — ไม่ใช่ข้อมูลตลาดจริง\n", encoding="utf-8")
    return folder
