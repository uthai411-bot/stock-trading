"""รวมปัจจัยทุกกลุ่มเป็นตารางเดียวบนปฏิทินของ S50"""
import pandas as pd

from ..config import FeatureParams
from ..data.loaders import Dataset
from .breadth import breadth_features
from .flow import flow_features
from .futures import basis_features, oi_regime, tfex_position_features
from .trend import trend_features


def build_features(ds: Dataset, p: FeatureParams) -> pd.DataFrame:
    parts = [
        ds.s50[["open", "high", "low", "close", "volume", "open_interest"]],
        ds.index.rename(columns={"close": "index_close"}),
        trend_features(ds.s50, p),
        flow_features(ds.set_investor, p),
        tfex_position_features(ds.tfex_investor, p),
        oi_regime(ds.s50, p),
        basis_features(ds.s50, ds.index, p),
        breadth_features(ds.constituents, ds.s50.index, p),
    ]
    feats = pd.concat([x for x in parts if not x.empty], axis=1)
    feats.index.name = "date"
    return feats


def factor_columns(feats: pd.DataFrame) -> list[str]:
    """คอลัมน์ที่ขึ้นต้น f_ คือปัจจัยที่ถูก normalize แล้ว พร้อมเข้าคะแนนรวม"""
    return [c for c in feats.columns if c.startswith("f_")]
