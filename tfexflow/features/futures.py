"""ปัจจัยจากตัว S50 Futures เอง: สถานะสุทธิรายกลุ่มใน TFEX · OI regime · basis"""
import numpy as np
import pandas as pd

from ..config import FeatureParams
from .common import rolling_z, squash


def tfex_position_features(tfex_inv: pd.DataFrame | None, p: FeatureParams) -> pd.DataFrame:
    """ยอด long-short สุทธิรายวัน (สัญญา) สะสมเป็น "สถานะสุทธิโดยประมาณ" แล้วดูการเปลี่ยนแปลง 5 วัน

    ★ ยอดสะสมจากศูนย์ไม่ใช่สถานะจริง (ไม่รู้จุดเริ่ม) แต่ "การเปลี่ยนแปลง" ของมันถูกต้อง
    """
    if tfex_inv is None:
        return pd.DataFrame()
    out = pd.DataFrame(index=tfex_inv.index)
    for typ in ("foreign", "institution", "local"):
        col = f"{typ}_net"
        if col not in tfex_inv.columns:
            continue
        net = tfex_inv[col].astype(float)
        out[f"tfex_{typ}_net"] = net
        out[f"tfex_{typ}_pos"] = net.cumsum()
        out[f"tfex_{typ}_chg{p.flow_short}"] = net.rolling(p.flow_short, min_periods=1).sum()
    if "tfex_foreign_net" in out:
        out["f_tfex_foreign_position"] = squash(rolling_z(out[f"tfex_foreign_chg{p.flow_short}"], p.zscore_window))
    return out


def oi_regime(s50: pd.DataFrame, p: FeatureParams) -> pd.DataFrame:
    """ราคา × OI สี่กรณี — ค่าจากการอ่านหน้าจอของนักวิเคราะห์เทคนิค แปลงเป็นตัวเลข

    ราคาขึ้น OI เพิ่ม → long ใหม่เข้า (+1) · ราคาลง OI เพิ่ม → short ใหม่เข้า (-1)
    ราคาขึ้น OI ลด → short ปิด (ขึ้นแบบอ่อน +0.5) · ราคาลง OI ลด → long ปิด (ลงแบบอ่อน -0.5)
    ใช้ค่าเฉลี่ย 5 วันของการเปลี่ยนแปลงเพื่อลดเสียงรบกวนรายวัน
    """
    out = pd.DataFrame(index=s50.index)
    dp = s50["close"].diff().rolling(p.flow_short, min_periods=1).sum()
    doi = s50["open_interest"].diff().rolling(p.flow_short, min_periods=1).sum()
    sp, so = np.sign(dp), np.sign(doi)
    regime = np.where(so > 0, sp, 0.5 * sp)
    out["oi_change5"] = doi
    out["f_oi_regime"] = pd.Series(regime, index=s50.index).fillna(0.0)
    return out


def basis_features(s50: pd.DataFrame, index: pd.DataFrame, p: FeatureParams) -> pd.DataFrame:
    """basis = futures − ดัชนี · เทียบกับค่าเฉลี่ยย้อนหลัง (แทนมูลค่ายุติธรรมที่ต้องใช้ดอกเบี้ย/ปันผล)

    basis สูงผิดปกติ = ตลาด futures ไล่ซื้อแรงกว่าหุ้น มักกลับตัวลง ⇒ ปัจจัยนี้เป็น **contrarian** (ใส่เครื่องหมายลบ)
    ★ ใกล้วันหมดอายุ basis จะวิ่งเข้าศูนย์ตามธรรมชาติ — ถ้าไฟล์ s50 roll ไม่ดี ปัจจัยนี้จะเพี้ยน ให้ตั้งน้ำหนัก 0
    """
    out = pd.DataFrame(index=s50.index)
    # ★ ไฟล์จาก `tfexflow roll` มีราคาปรับย้อนหลัง — basis ต้องใช้ราคาจริงของซีรีส์ (close_raw)
    fut = s50["close_raw"] if "close_raw" in s50.columns else s50["close"]
    out["basis"] = fut - index["close"]
    out["basis_z"] = rolling_z(out["basis"], p.basis_window)
    out["f_basis"] = -squash(out["basis_z"])
    return out
