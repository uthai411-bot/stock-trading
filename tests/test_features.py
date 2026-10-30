import numpy as np
import pandas as pd

from tfexflow.config import DEFAULT
from tfexflow.data import synthetic
from tfexflow.data.loaders import load
from tfexflow.features import build_features
from tfexflow.features.common import rolling_z, squash
from tfexflow.features.futures import oi_regime


def test_zscore_ถูกตัดที่บวกลบ4_และ_squash_อยู่ในช่วง():
    s = pd.Series(np.r_[np.zeros(100), 1e6])
    z = rolling_z(s, 50)
    assert z.iloc[-1] == 4
    assert squash(z).abs().max() < 1


def test_oi_regime_สี่กรณี():
    idx = pd.bdate_range("2025-01-01", periods=12)
    close = pd.Series([100, 101, 102, 103, 104, 105, 104, 103, 102, 101, 100, 99], index=idx, dtype=float)
    oi = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21], index=idx, dtype=float)
    s50 = pd.DataFrame({"close": close, "open_interest": oi})
    r = oi_regime(s50, DEFAULT.features)["f_oi_regime"]
    assert r.iloc[5] == 1.0      # ราคาขึ้น OI เพิ่ม → long ใหม่
    assert r.iloc[-1] == -1.0    # ราคาลง OI เพิ่ม → short ใหม่
    oi2 = oi[::-1].set_axis(idx)
    r2 = oi_regime(pd.DataFrame({"close": close, "open_interest": oi2}), DEFAULT.features)["f_oi_regime"]
    assert r2.iloc[5] == 0.5     # ราคาขึ้น OI ลด → short ปิด
    assert r2.iloc[-1] == -0.5   # ราคาลง OI ลด → long ปิด


def test_ไม่มองอนาคต_แก้ข้อมูลวันหลังไม่กระทบปัจจัยวันก่อน(tmp_path):
    folder = synthetic.write(tmp_path / "a", years=2, seed=3)
    ds = load(folder)
    base = build_features(ds, DEFAULT.features)
    cut = base.index[-60]
    # ตัดข้อมูลหลังวัน cut ทิ้งทั้งหมด แล้วคำนวณใหม่ — ปัจจัยถึงวัน cut ต้องเท่าเดิมทุกตัว
    ds.s50 = ds.s50.loc[:cut]; ds.index = ds.index.loc[:cut]
    ds.set_investor = ds.set_investor.loc[:cut]; ds.tfex_investor = ds.tfex_investor.loc[:cut]
    ds.constituents = ds.constituents[ds.constituents["date"] <= cut]
    trunc = build_features(ds, DEFAULT.features)
    pd.testing.assert_frame_equal(base.loc[:cut], trunc, check_like=True)


def test_ปัจจัยที่ไม่มีไฟล์_ถูกข้ามไม่พัง(tmp_path):
    folder = synthetic.write(tmp_path / "b", years=1, seed=1)
    (folder / "tfex_investor_daily.csv").unlink(); (folder / "constituents_daily.csv").unlink()
    ds = load(folder)
    f = build_features(ds, DEFAULT.features)
    assert "f_set_foreign_flow" in f and "f_tfex_foreign_position" not in f and "f_breadth" not in f
