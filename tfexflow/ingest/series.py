"""รหัสซีรีส์ S50 Futures และวันซื้อขายวันสุดท้าย

รหัส = S50 + ตัวอักษรเดือน + ปี ค.ศ. 2 หลัก · เช่น S50Z26 = ธันวาคม 2026
วันซื้อขายวันสุดท้ายของ S50 = วันทำการก่อนวันทำการสุดท้ายของเดือนที่ครบกำหนด

★ ฟังก์ชันนี้นับเฉพาะเสาร์–อาทิตย์ ยังไม่รู้วันหยุดตลาดไทย — ใกล้สิ้นเดือนที่มีวันหยุดอาจเพี้ยนหนึ่งวัน
ใช้วางแผนว่าจะดึงซีรีส์ไหนเท่านั้น · การ roll จริงตัดสินจากข้อมูล (OI/วอลุ่ม) ไม่ใช่วันที่นี้
"""
from datetime import date

import pandas as pd

MONTH_CODES = "FGHJKMNQUVXZ"


def parse(code: str) -> tuple[str, int, int]:
    """'S50Z26' → ('S50', 2026, 12)"""
    code = code.strip().upper()
    if len(code) < 4 or code[-3] not in MONTH_CODES or not code[-2:].isdigit():
        raise ValueError(f"รหัสซีรีส์ {code!r} ไม่ใช่รูปแบบ <สินค้า><ตัวอักษรเดือน><ปี 2 หลัก> เช่น S50Z26")
    return code[:-3], 2000 + int(code[-2:]), MONTH_CODES.index(code[-3]) + 1


def make(underlying: str, year: int, month: int) -> str:
    return f"{underlying}{MONTH_CODES[month - 1]}{year % 100:02d}"


def last_trading_day(code: str) -> date:
    _, y, m = parse(code)
    bdays = pd.bdate_range(date(y, m, 1), pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0))
    return bdays[-2].date()


def series_between(start: str | date, end: str | date, underlying: str = "S50") -> list[str]:
    """ทุกซีรีส์รายเดือนที่ครบกำหนดตั้งแต่ start ถึง end + 3 เดือน (ครอบคลุมสัญญาที่ซื้อขายอยู่ในช่วงนั้น)"""
    s = pd.Timestamp(start).to_period("M")
    e = (pd.Timestamp(end) + pd.offsets.MonthEnd(3)).to_period("M")
    return [make(underlying, p.year, p.month) for p in pd.period_range(s, e, freq="M")]
