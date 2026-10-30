"""ขั้นที่ 1 — วัดอำนาจทำนายของแต่ละปัจจัยต่อผลตอบแทน S50 ล่วงหน้า **ก่อน** เชื่อสมมุติฐาน

วิธีวัด (ต่อปัจจัย ต่อระยะ h วัน):
  IC          = Spearman rank correlation ระหว่างปัจจัย ณ ปิดวัน t กับผลตอบแทน open(t+1) → close(t+h)
  t-stat      = IC·√(n−2)/√(1−IC²) หารด้วย √h ชดเชยที่หน้าต่างซ้อนกัน (ประมาณการแบบอนุรักษ์)
  quintile    = ผลตอบแทนเฉลี่ย (จุด) เมื่อแบ่งปัจจัยเป็น 5 ชั้น · Q5−Q1 คือ "spread"
  hit rate    = สัดส่วนที่เครื่องหมายของปัจจัยตรงกับเครื่องหมายของผลตอบแทน

เกณฑ์อ่านผล (เขียนไว้ที่นี่เพื่อไม่ให้ตีความตามใจทีหลัง):
  |t| ≥ 2.0 และ spread หลังหักต้นทุนไปกลับยังเป็นบวก  → ปัจจัยนี้ "น่าใช้"
  |t| < 1.0                                        → น้ำหนักควรเป็น 0
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..config import ContractSpec, CostModel

HORIZONS = (1, 2, 3, 5, 10)


def forward_returns(feats: pd.DataFrame, horizons=HORIZONS) -> pd.DataFrame:
    """ผลตอบแทนที่ "ทำได้จริง": เข้า open วัน t+1 ออก close วัน t+h · หน่วยเป็นจุด"""
    out = pd.DataFrame(index=feats.index)
    nxt_open = feats["open"].shift(-1)
    for h in horizons:
        out[f"fwd_{h}"] = feats["close"].shift(-h) - nxt_open
    return out


@dataclass
class FactorResult:
    factor: str
    horizon: int
    n: int
    ic: float
    t_stat: float
    hit_rate: float
    q1: float
    q5: float
    spread: float
    spread_after_cost: float


def evaluate(feats: pd.DataFrame, factors: list[str] | None = None, horizons=HORIZONS,
             cost: CostModel = CostModel(), spec: ContractSpec = ContractSpec()) -> pd.DataFrame:
    factors = factors or [c for c in feats.columns if c.startswith("f_") or c == "score"]
    fwd = forward_returns(feats, horizons)
    rt_cost = cost.round_trip_points(spec)
    rows: list[FactorResult] = []
    for f in factors:
        if f not in feats.columns:
            continue
        for h in horizons:
            df = pd.concat([feats[f], fwd[f"fwd_{h}"]], axis=1).dropna()
            df.columns = ["x", "y"]
            df = df[df["x"] != 0]  # ค่า 0 = ไม่มีความเห็น ไม่นับ
            n = len(df)
            if n < 30:
                continue
            ic = float(df["x"].rank().corr(df["y"].rank()))  # Spearman = Pearson ของอันดับ (ไม่พึ่ง scipy)
            t = ic * np.sqrt(n - 2) / np.sqrt(max(1e-9, 1 - ic**2)) / np.sqrt(h)
            hit = float((np.sign(df["x"]) == np.sign(df["y"])).mean())
            try:
                q = pd.qcut(df["x"], 5, labels=False, duplicates="drop")
                means = df.groupby(q)["y"].mean()
                q1, q5 = float(means.iloc[0]), float(means.iloc[-1])
            except ValueError:
                q1 = q5 = float("nan")
            spread = q5 - q1
            rows.append(FactorResult(f, h, n, ic, float(t), hit, q1, q5, spread, spread - rt_cost))
    return pd.DataFrame([r.__dict__ for r in rows])


def verdict(table: pd.DataFrame) -> pd.DataFrame:
    """สรุปต่อปัจจัย: ระยะที่ดีที่สุดและคำตัดสินตามเกณฑ์ในหัวไฟล์"""
    if table.empty:
        return table
    best = table.loc[table.groupby("factor")["t_stat"].apply(lambda s: s.abs().idxmax())]
    def judge(r):
        if abs(r.t_stat) >= 2.0 and r.spread_after_cost > 0:
            return "น่าใช้"
        if abs(r.t_stat) < 1.0:
            return "ไม่มีสัญญาณ → น้ำหนัก 0"
        return "อ่อน — ใช้ร่วมกับปัจจัยอื่นเท่านั้น"
    best = best.assign(verdict=best.apply(judge, axis=1))
    return best.sort_values("t_stat", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)
