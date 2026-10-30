"""บันทึกยอดซื้อขายรายกลุ่มรายวันด้วยมือ — สำหรับช่วงที่ยังไม่ได้สมัครแหล่งข้อมูลแบบ API

ที่มาตัวเลข: หน้า Investor Type ของ set.or.th (หุ้น · ล้านบาท) และหน้า Trading by Investor Types
ของ tfex.co.th (S50 · สัญญา) — ประกาศหลังตลาดปิดทุกวัน กรอกวันละครั้ง ใช้เวลาไม่ถึงนาที

★ บันทึกซ้ำวันเดิมจะถูกปฏิเสธ (ไม่เขียนทับเงียบ ๆ) — ถ้ากรอกผิดให้แก้ไฟล์ CSV เองแล้วรันตรวจ
"""
from pathlib import Path

import pandas as pd

from ..data import schemas as S

SET_TYPES = ("foreign", "institution", "proprietary", "retail")
TFEX_TYPES = ("foreign", "institution", "local")


def append(folder: str | Path, market: str, day: str, values: dict[str, tuple[float, float]]) -> Path:
    """values = {'foreign': (ซื้อ, ขาย), ...} · market = 'set' หรือ 'tfex'"""
    if market == "set":
        schema, types, cols = S.SET_INVESTOR, SET_TYPES, ("buy_value", "sell_value")
    elif market == "tfex":
        schema, types, cols = S.TFEX_INVESTOR, TFEX_TYPES, ("long_contracts", "short_contracts")
    else:
        raise ValueError("market ต้องเป็น set หรือ tfex")
    missing = [t for t in types if t not in values]
    if missing:
        raise ValueError(f"ยังไม่ได้กรอกกลุ่ม {', '.join(missing)} — ต้องครบทุกกลุ่มในวันเดียวกัน")
    pd.Timestamp(day)  # ตรวจรูปแบบวันที่ก่อน
    path = Path(folder) / schema.filename
    new = pd.DataFrame([{"date": day, "investor_type": t, cols[0]: values[t][0], cols[1]: values[t][1]}
                        for t in types])
    old = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=new.columns)
    if (old["date"].astype(str) == day).any():
        raise ValueError(f"มีข้อมูลวันที่ {day} ในไฟล์ {schema.filename} แล้ว — ถ้าจะแก้ให้แก้ในไฟล์โดยตรง")
    merged = pd.concat([old, new], ignore_index=True)
    S.validate(merged, schema)  # ด่านเดียวกับตอนโหลด — ผิดรูปแบบ = ไม่เขียน
    if market == "set":
        net = sum(values[t][0] - values[t][1] for t in types)
        if abs(net) > 1.0:
            raise ValueError(f"ยอดสุทธิทุกกลุ่มรวมกันต้องเป็นศูนย์ (ได้ {net:,.2f} ล้านบาท) — ตรวจตัวเลขที่กรอกอีกครั้ง")
    Path(folder).mkdir(parents=True, exist_ok=True)
    merged.to_csv(path, index=False)
    return path
