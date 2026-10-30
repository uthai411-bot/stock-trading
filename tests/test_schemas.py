import pandas as pd
import pytest

from tfexflow.data import schemas as S


def test_ขาดคอลัมน์_บอกชื่อไฟล์และคอลัมน์():
    df = pd.DataFrame({"date": ["2025-01-02"], "close": [1.0]})
    with pytest.raises(S.DataFormatError) as e:
        S.validate(df, S.S50_DAILY)
    assert "s50_daily.csv" in str(e.value) and "open" in str(e.value)


def test_วันซ้ำ_โยน_error():
    df = pd.DataFrame({"date": ["2025-01-02", "2025-01-02"], "close": [1.0, 2.0]})
    with pytest.raises(S.DataFormatError) as e:
        S.validate(df, S.SET50_INDEX)
    assert "ซ้ำ" in str(e.value)


def test_ตัวเลขผิดรูป_บอกบรรทัด():
    df = pd.DataFrame({"date": ["2025-01-02", "2025-01-03"], "close": ["1.0", "abc"]})
    with pytest.raises(S.DataFormatError) as e:
        S.validate(df, S.SET50_INDEX)
    assert "บรรทัดที่ 3" in str(e.value)


def test_กลุ่มผู้ลงทุนที่ไม่รู้จัก_โยน_error():
    df = pd.DataFrame({"date": ["2025-01-02"], "investor_type": ["alien"], "buy_value": [1], "sell_value": [1]})
    with pytest.raises(S.DataFormatError) as e:
        S.validate(df, S.SET_INVESTOR)
    assert "alien" in str(e.value)


def test_พ_ศ_ในไฟล์_ถูกปฏิเสธ():
    df = pd.DataFrame({"date": ["2568-01-02"], "close": [1.0]})
    out = S.validate(df, S.SET50_INDEX)
    # pandas รับ 2568 เป็น ค.ศ. 2568 ได้ — เราไม่เดาแทนผู้ใช้ แต่เอกสารระบุชัดว่าต้องเป็น ค.ศ.
    assert out["date"].iloc[0].year == 2568
