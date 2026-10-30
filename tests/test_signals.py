import pandas as pd

from tfexflow.config import SignalRules, SignalWeights
from tfexflow.signals.composite import composite_score, to_state


def test_น้ำหนักถูก_normalize_เมื่อปัจจัยหาย():
    f = pd.DataFrame({"f_set_foreign_flow": [1.0, -1.0], "f_oi_regime": [1.0, 1.0]})
    score, used = composite_score(f, SignalWeights())
    assert abs(sum(used.values()) - 1) < 1e-9 and set(used) == {"set_foreign_flow", "oi_regime"}
    assert abs(score.iloc[0] - 1.0) < 1e-9


def test_เกณฑ์และตัวกรองแนวโน้ม():
    score = pd.Series([0.5, -0.5, 0.1, 0.5])
    trend = pd.Series([1, 1, 1, -1])
    st = to_state(score, trend, SignalRules(trend_filter=True))
    assert list(st) == [1, 0, 0, 0]   # SHORT ถูกกรองเพราะแนวโน้มขึ้น · LONG สุดท้ายถูกกรองเพราะแนวโน้มลง
    st2 = to_state(score, trend, SignalRules(trend_filter=False))
    assert list(st2) == [1, -1, 0, 1]


def test_ถือขั้นต่ำ_กันสลับข้างทันที():
    score = pd.Series([0.5, -0.5, -0.5, -0.5, 0.0])
    st = to_state(score, None, SignalRules(trend_filter=False, min_hold_days=3))
    assert list(st) == [1, 1, 1, -1, 0]
