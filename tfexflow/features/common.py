import numpy as np
import pandas as pd


def rolling_z(s: pd.Series, window: int, min_periods: int | None = None) -> pd.Series:
    """z-score เทียบหน้าต่างย้อนหลัง · ค่าสุดขั้วตัดที่ ±4 กันตัวเดียวลากคะแนนรวม"""
    mp = min_periods or max(20, window // 4)
    mu = s.rolling(window, min_periods=mp).mean()
    sd = s.rolling(window, min_periods=mp).std()
    z = (s - mu) / sd.replace(0, np.nan)
    return z.clip(-4, 4)


def squash(z: pd.Series, scale: float = 1.5) -> pd.Series:
    """แปลง z-score เป็นช่วง (-1, 1) ด้วย tanh เพื่อให้ทุกปัจจัยอยู่สเกลเดียวกันก่อนถ่วงน้ำหนัก"""
    return np.tanh(z / scale)
