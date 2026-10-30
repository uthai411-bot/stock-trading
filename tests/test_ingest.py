import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tfexflow.cli import main
from tfexflow.ingest import flowlog, roll, series, settrade
from tfexflow.ingest.envfile import load_env


# ───────── รหัสซีรีส์ ─────────

def test_อ่านและสร้างรหัสซีรีส์():
    assert series.parse("S50Z26") == ("S50", 2026, 12)
    assert series.make("S50", 2027, 3) == "S50H27"
    with pytest.raises(ValueError):
        series.parse("S50-DEC")


def test_วันซื้อขายสุดท้าย_คือวันทำการก่อนวันทำการสุดท้ายของเดือน():
    # ธ.ค. 2026: วันทำการสุดท้าย = พฤ. 31 → วันซื้อขายสุดท้าย = พ. 30
    assert str(series.last_trading_day("S50Z26")) == "2026-12-30"
    assert series.series_between("2026-11-01", "2026-12-15")[:3] == ["S50X26", "S50Z26", "S50F27"]


# ───────── ต่อซีรีส์ ─────────

def _series(start, n, base, oi_start, oi_step):
    idx = pd.bdate_range(start, periods=n)
    c = base + np.arange(n, dtype=float)
    return pd.DataFrame({"open": c - .5, "high": c + 1, "low": c - 1, "close": c, "volume": 100.0,
                         "open_interest": oi_start + oi_step * np.arange(n, dtype=float)}, index=idx)


def test_roll_ตาม_OI_และไม่ย้อนกลับ():
    a = _series("2026-01-05", 10, 1000, 1000, -100)   # OI ลดลงเรื่อย ๆ
    b = _series("2026-01-05", 15, 1010, 100, 100)     # OI เพิ่มขึ้น · แพงกว่า 10 จุด (basis)
    cont = roll.build_continuous({"S50G26": a, "S50H26": b})
    first_b = cont.index[cont["series"] == "S50H26"][0]
    assert (cont.loc[first_b:, "series"] == "S50H26").all()          # ไม่กลับไปซีรีส์เก่า
    assert b.loc[first_b, "open_interest"] > a.loc[first_b, "open_interest"]


def test_back_adjust_ไม่มีกำไรปลอมวัน_roll_และราคาล่าสุดเป็นราคาจริง():
    a = _series("2026-01-05", 10, 1000, 1000, -100)
    b = _series("2026-01-05", 15, 1010, 100, 100)
    cont = roll.build_continuous({"S50G26": a, "S50H26": b})
    # ทั้งสองซีรีส์ขึ้นวันละ 1 จุดพอดี ⇒ ส่วนต่างรายวันของเส้นต่อเนื่องต้องเป็น 1 ทุกวัน แม้วัน roll
    assert np.allclose(cont["close"].diff().dropna(), 1.0)
    assert cont["close"].iloc[-1] == b["close"].iloc[-1] == cont["close_raw"].iloc[-1]
    assert cont["close_raw"].iloc[0] == a["close"].iloc[0]


def test_roll_ใช้วอลุ่มเมื่อไม่มี_OI():
    a = _series("2026-01-05", 6, 1000, 0, 0).assign(open_interest=np.nan, volume=[9, 9, 9, 1, 1, 1])
    b = _series("2026-01-05", 8, 1005, 0, 0).assign(open_interest=np.nan, volume=[1, 1, 1, 9, 9, 9, 9, 9])
    cont = roll.build_continuous({"S50G26": a, "S50H26": b})
    assert cont["series"].tolist()[:4] == ["S50G26"] * 3 + ["S50H26"]


def test_คำสั่ง_roll_เขียนไฟล์ที่ระบบโหลดได้(tmp_path):
    sdir = tmp_path / "series"; sdir.mkdir()
    for code, df in {"S50G26": _series("2026-01-05", 10, 1000, 1000, -100),
                     "S50H26": _series("2026-01-05", 15, 1010, 100, 100)}.items():
        df.rename_axis("date").reset_index().assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d")) \
            .to_csv(sdir / f"{code}.csv", index=False)
    assert main(["roll", "--series-dir", str(sdir), "--out", str(tmp_path)]) == 0
    from tfexflow.data import schemas as S
    out = S.validate(pd.read_csv(tmp_path / "s50_daily.csv"), S.S50_DAILY)
    assert {"close_raw", "series"} <= set(out.columns) and len(out) == 15


# ───────── Settrade ─────────

def test_แปลงแท่งเทียน_ทั้งสองรูปแบบ():
    t0 = int(pd.Timestamp("2026-10-29 09:45", tz="Asia/Bangkok").timestamp())
    d = {"time": [t0, t0 + 86400], "open": [1, 2], "high": [2, 3], "low": [0.5, 1.5], "close": [1.5, 2.5],
         "volume": [10, 20], "value": [0, 0]}
    df = settrade.candles_to_frame(d)
    assert [str(x.date()) for x in df.index] == ["2026-10-29", "2026-10-30"]
    lst = [{"time": t0 * 1000, "open": 1, "high": 2, "low": .5, "close": 1.5, "volume": 10}]
    assert settrade.candles_to_frame(lst)["close"].iloc[0] == 1.5
    with pytest.raises(ValueError):
        settrade.candles_to_frame({"unexpected": 1})


def test_settrade_ไม่มีค่าใน_env_บอกชัด(monkeypatch):
    for k in settrade.REQUIRED_ENV:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(settrade.SettradeConfigError) as e:
        settrade.market_from_env()
    assert "SETTRADE_APP_ID" in str(e.value)


def test_settrade_ไม่แตะโมดูลส่งคำสั่ง():
    """★ แผนที่ตกลง: ยังไม่ส่งคำสั่งจริง — ตัวดึงข้อมูลต้องไม่เรียก Derivatives/Equity/place_order"""
    src = Path(settrade.__file__).read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    code = code.split('"""', 2)[-1]  # ตัด docstring หัวไฟล์ที่อธิบายข้อห้ามนี้ออก
    for bad in (".Derivatives(", ".Equity(", "place_order", "cancel_order", "change_order"):
        assert bad not in code


def test_fetch_ใช้ตัวปลอมแทน_API(monkeypatch, tmp_path):
    class FakeMarket:
        def get_candlestick(self, symbol, interval, start=None, end=None, **kw):
            assert interval == "1d"
            if symbol not in ("S50X26", "SET50"):
                return {"time": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
            t = int(pd.Timestamp("2026-10-29", tz="Asia/Bangkok").timestamp())
            return {"time": [t], "open": [1000], "high": [1005], "low": [995], "close": [1001], "volume": [5]}
    monkeypatch.setattr(settrade, "market_from_env", lambda: FakeMarket())
    assert main(["fetch", "--start", "2026-10-01", "--end", "2026-10-29", "--out", str(tmp_path),
                 "--env", str(tmp_path / "none.env")]) == 0
    assert (tmp_path / "series" / "S50X26.csv").exists() and (tmp_path / "set50_index_daily.csv").exists()


def test_อ่าน_env_ไม่ทับค่าที่มีอยู่(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text("# c\nA_X=1\nexport A_Y='2'\nA_Z=3\n", encoding="utf-8")
    monkeypatch.setenv("A_Z", "keep")
    monkeypatch.delenv("A_X", raising=False); monkeypatch.delenv("A_Y", raising=False)
    assert load_env(p) == ["A_X", "A_Y", "A_Z"]
    assert os.environ["A_X"] == "1" and os.environ["A_Y"] == "2" and os.environ["A_Z"] == "keep"


# ───────── กรอกยอดรายกลุ่มด้วยมือ ─────────

def test_กรอกยอด_SET_รายวัน_และกันวันซ้ำ(tmp_path):
    v = {"foreign": (30000, 32860), "institution": (5000, 4000), "proprietary": (6000, 5900),
         "retail": (25000, 23240)}
    flowlog.append(tmp_path, "set", "2026-10-29", v)
    df = pd.read_csv(tmp_path / "set_investor_daily.csv")
    assert len(df) == 4
    with pytest.raises(ValueError, match="มีข้อมูลวันที่"):
        flowlog.append(tmp_path, "set", "2026-10-29", v)


def test_กรอกยอดไม่ดุล_ถูกปฏิเสธ(tmp_path):
    v = {"foreign": (30000, 32860), "institution": (5000, 4000), "proprietary": (6000, 5900),
         "retail": (25000, 25000)}
    with pytest.raises(ValueError, match="ศูนย์"):
        flowlog.append(tmp_path, "set", "2026-10-29", v)
    assert not (tmp_path / "set_investor_daily.csv").exists()


def test_คำสั่ง_add_flow_TFEX(tmp_path):
    assert main(["add-flow", "tfex", "--date", "2026-10-29", "--data", str(tmp_path),
                 "--foreign", "60,000/58,500", "--institution", "20000/21000", "--local", "90000/90500"]) == 0
    df = pd.read_csv(tmp_path / "tfex_investor_daily.csv")
    assert set(df["investor_type"]) == {"foreign", "institution", "local"}
