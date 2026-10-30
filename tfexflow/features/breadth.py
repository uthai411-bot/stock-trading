"""หุ้น 50 ตัวในดัชนี: breadth และ money flow ถ่วงน้ำหนัก

money flow ต่อตัวใช้ OBV รายวัน (volume × sign ของการเปลี่ยนราคา) เพราะไฟล์มีแค่ close/volume
ถ้าวันหน้ามี tick data จะเปลี่ยนเป็น volume delta ของจริงได้โดยไม่กระทบส่วนอื่น (ชื่อคอลัมน์ผลลัพธ์เดิม)
"""
import numpy as np
import pandas as pd

from ..config import FeatureParams
from .common import rolling_z, squash


def breadth_features(cons: pd.DataFrame | None, calendar: pd.DatetimeIndex, p: FeatureParams) -> pd.DataFrame:
    if cons is None or cons.empty:
        return pd.DataFrame()
    close = cons.pivot(index="date", columns="symbol", values="close").sort_index()
    vol = cons.pivot(index="date", columns="symbol", values="volume").sort_index()
    w = cons.pivot(index="date", columns="symbol", values="weight").sort_index()
    w = w.where(w.sum(axis=1) > 0, 1.0)          # ไม่มีน้ำหนัก → ถ่วงเท่ากัน
    w = w.div(w.sum(axis=1), axis=0)

    ema = close.ewm(span=p.breadth_ema, adjust=False).mean()
    above = (close > ema).astype(float)
    out = pd.DataFrame(index=close.index)
    out["breadth_pct_above_ema"] = above.mean(axis=1)
    out["breadth_weighted"] = (above * w).sum(axis=1)
    adv = (close.diff() > 0).sum(axis=1); dec = (close.diff() < 0).sum(axis=1)
    out["adv_dec"] = adv - dec

    # money flow: OBV รายตัว normalize ด้วยวอลุ่มเฉลี่ย 20 วันของตัวเอง แล้วถ่วงน้ำหนักดัชนี
    sign = np.sign(close.diff()).fillna(0.0)
    vol_norm = vol / vol.rolling(20, min_periods=5).mean()
    mf = (sign * vol_norm * w).sum(axis=1)
    out["money_flow"] = mf
    out["money_flow_cum5"] = mf.rolling(p.flow_short, min_periods=1).sum()

    # ปัจจัยเข้าคะแนนรวม — breadth ใช้ระยะจาก 0.5 (ครึ่งหนึ่งของหุ้นยืนเหนือ EMA = กลาง)
    out["f_breadth"] = squash((out["breadth_weighted"] - 0.5) * 4)
    out["f_money_flow"] = squash(rolling_z(out["money_flow_cum5"], p.zscore_window))
    return out.reindex(calendar).ffill()
