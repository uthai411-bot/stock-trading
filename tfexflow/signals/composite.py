"""รวมปัจจัยเป็นคะแนนเดียวแล้วแปลงเป็นสถานะ LONG / SHORT / FLAT

คะแนนรวม ∈ [-1, 1] · ปัจจัยที่ไม่มีข้อมูล (คอลัมน์หาย) ถูกตัดออกและ normalize น้ำหนักที่เหลือ
สถานะของวัน t คือ "สิ่งที่จะทำตอนเปิดวัน t+1" — backtest ใช้ open ของวันถัดไปเสมอ
"""
import numpy as np
import pandas as pd

from ..config import SignalRules, SignalWeights

LONG, SHORT, FLAT = 1, -1, 0


def composite_score(feats: pd.DataFrame, weights: SignalWeights) -> tuple[pd.Series, dict[str, float]]:
    """คืน (คะแนนรวม, น้ำหนักที่ใช้จริงหลังตัดปัจจัยที่ไม่มีข้อมูล)"""
    raw = weights.as_dict()
    used = {k: v for k, v in raw.items() if f"f_{k}" in feats.columns and v != 0}
    total = sum(abs(v) for v in used.values())
    if total == 0:
        return pd.Series(0.0, index=feats.index, name="score"), {}
    used = {k: v / total for k, v in used.items()}
    score = sum(feats[f"f_{k}"].fillna(0.0) * w for k, w in used.items())
    return score.clip(-1, 1).rename("score"), used


def to_state(score: pd.Series, trend: pd.Series | None, rules: SignalRules) -> pd.Series:
    """แปลงคะแนนเป็น 1 / -1 / 0 พร้อมตัวกรองแนวโน้มและถือขั้นต่ำ"""
    desired = pd.Series(FLAT, index=score.index, dtype=int)
    desired[score >= rules.long_threshold] = LONG
    desired[score <= rules.short_threshold] = SHORT
    if rules.trend_filter and trend is not None:
        t = trend.reindex(score.index).fillna(0)
        desired[(desired == LONG) & (t < 0)] = FLAT
        desired[(desired == SHORT) & (t > 0)] = FLAT
    if rules.min_hold_days <= 1:
        return desired.rename("state")
    # ถือขั้นต่ำ: เปลี่ยนสถานะได้เมื่อถือมาครบ min_hold_days แล้วเท่านั้น (ยกเว้นกลับเป็น FLAT ได้เสมอ)
    out = np.zeros(len(desired), dtype=int); held = 0
    for i, d in enumerate(desired.to_numpy()):
        prev = out[i - 1] if i else FLAT
        if d == prev:
            out[i] = prev; held += 1
        elif prev != FLAT and d != FLAT and held < rules.min_hold_days:
            out[i] = prev; held += 1
        else:
            out[i] = d; held = 1
    return pd.Series(out, index=score.index, name="state")


def state_label(state: int) -> str:
    return {LONG: "LONG", SHORT: "SHORT"}.get(int(state), "FLAT")
