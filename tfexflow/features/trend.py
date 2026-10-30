"""แนวโน้มและความผันผวนของ S50 — ใช้เป็นตัวกรองและกำหนดขนาดสถานะ ไม่ใช่สัญญาณหลัก"""
import pandas as pd

from ..config import FeatureParams


def trend_features(s50: pd.DataFrame, p: FeatureParams) -> pd.DataFrame:
    out = pd.DataFrame(index=s50.index)
    c = s50["close"]
    out["ema_fast"] = c.ewm(span=p.ema_fast, adjust=False).mean()
    out["ema_slow"] = c.ewm(span=p.ema_slow, adjust=False).mean()
    out["trend"] = ((c > out["ema_slow"]).astype(int) - (c < out["ema_slow"]).astype(int)).astype(float)
    prev_close = c.shift(1)
    tr = pd.concat([s50["high"] - s50["low"], (s50["high"] - prev_close).abs(),
                    (s50["low"] - prev_close).abs()], axis=1).max(axis=1)
    out["atr"] = tr.ewm(alpha=1 / p.atr_window, adjust=False, min_periods=p.atr_window).mean()
    out["ret_1d"] = c.pct_change()
    return out
