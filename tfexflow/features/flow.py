"""กระแสเงินรายกลุ่มในตลาดหุ้น (ล้านบาท) → ปัจจัยมาตรฐาน

ทำไมใช้ยอดสะสม 5 วันแทนยอดวันเดียว: ยอดวันเดียวมีเสียงรบกวนจาก arbitrage และ program trading สูง
ยอดสะสมสั้น ๆ สะท้อน "ทิศทางที่ตั้งใจ" ชัดกว่า · ยอดสะสม 20 วันใช้บอกระบอบ (regime)
"""
import pandas as pd

from ..config import FeatureParams
from .common import rolling_z, squash


def flow_features(set_inv: pd.DataFrame, p: FeatureParams) -> pd.DataFrame:
    out = pd.DataFrame(index=set_inv.index)
    for typ in ("foreign", "institution", "proprietary", "retail"):
        col = f"{typ}_net"
        if col not in set_inv.columns:
            continue
        net = set_inv[col].astype(float)
        out[f"{typ}_net"] = net
        out[f"{typ}_cum{p.flow_short}"] = net.rolling(p.flow_short, min_periods=1).sum()
        out[f"{typ}_cum{p.flow_long}"] = net.rolling(p.flow_long, min_periods=1).sum()
        out[f"{typ}_z{p.flow_short}"] = rolling_z(out[f"{typ}_cum{p.flow_short}"], p.zscore_window)
        out[f"{typ}_z{p.flow_long}"] = rolling_z(out[f"{typ}_cum{p.flow_long}"], p.zscore_window)
    # ปัจจัยที่เข้าคะแนนรวม
    if "foreign_net" in out:
        out["f_set_foreign_flow"] = squash(out[f"foreign_z{p.flow_short}"])
    if "institution_net" in out:
        out["f_set_institution_flow"] = squash(out[f"institution_z{p.flow_short}"])
    return out
