from tfexflow.config import DEFAULT
from tfexflow.data import synthetic
from tfexflow.data.loaders import load
from tfexflow.features import build_features
from tfexflow.research.hypothesis import evaluate, forward_returns, verdict


def _best(folder, factor):
    feats = build_features(load(folder), DEFAULT.features)
    v = verdict(evaluate(feats, factors=[factor]))
    return v.iloc[0]


def test_ผลตอบแทนล่วงหน้าเริ่มที่_open_วันถัดไป(feats):
    fwd = forward_returns(feats, (1,))
    i = 10
    assert fwd["fwd_1"].iloc[i] == feats["close"].iloc[i + 1] - feats["open"].iloc[i + 1]


def test_ตรวจพบผลที่ฝังไว้เมื่อแรง(tmp_path):
    folder = synthetic.write(tmp_path / "strong", years=4, seed=5, flow_effect=0.006)
    r = _best(folder, "f_set_foreign_flow")
    assert r.t_stat > 2.0 and r.verdict == "น่าใช้"


def test_ไม่หลอกตัวเองเมื่อไม่มีผล(tmp_path):
    folder = synthetic.write(tmp_path / "null", years=4, seed=9, flow_effect=0.0)
    r = _best(folder, "f_set_foreign_flow")
    assert abs(r.t_stat) < 2.0 and r.verdict != "น่าใช้"
