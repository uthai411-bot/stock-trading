# รูปแบบไฟล์ข้อมูล

วางไฟล์ CSV ต่อไปนี้ในโฟลเดอร์เดียวกัน (เช่น `data/real/`) · วันที่เป็น `YYYY-MM-DD` ค.ศ. · encoding UTF-8
ไฟล์ที่มี ★ จำเป็น · ไฟล์ที่ไม่มี ★ ถ้าไม่มี ระบบจะข้ามปัจจัยนั้นและลดน้ำหนักให้อัตโนมัติ

| ไฟล์ | คอลัมน์ | ที่มา |
|---|---|---|
| ★ `s50_daily.csv` | `date, open, high, low, close, volume, open_interest` | S50 Futures สัญญาใกล้สุด (roll เมื่อ OI ของสัญญาถัดไปสูงกว่า) · TFEX / โบรกเกอร์ |
| ★ `set50_index_daily.csv` | `date, close` | ดัชนี SET50 ปิดวัน · SET |
| ★ `set_investor_daily.csv` | `date, investor_type, buy_value, sell_value` | ยอดซื้อขายรายกลุ่ม ตลาดหุ้น (ล้านบาท) · investor_type ∈ foreign, institution, proprietary, retail · SET "Investor Type" |
| `tfex_investor_daily.csv` | `date, investor_type, long_contracts, short_contracts` | S50 Futures รายกลุ่ม (สัญญา) · investor_type ∈ foreign, institution, local · TFEX "Trading by Investor Type" |
| `constituents_daily.csv` | `date, symbol, close, volume, weight` | หุ้น SET50 รายตัว · weight = น้ำหนักในดัชนี (0–1) ถ้าไม่มีให้ใส่ 0 ระบบจะถ่วงเท่ากัน |

`s50_daily.csv` ที่สร้างด้วย `python3 -m tfexflow roll` มีคอลัมน์เพิ่ม `close_raw, series, roll_adjustment`
ราคา open/high/low/close ในไฟล์นั้นถูกปรับย้อนหลังที่วัน roll · basis คำนวณจาก `close_raw`

ไฟล์รายซีรีส์สำหรับ `roll`: หนึ่งไฟล์ต่อซีรีส์ ชื่อ `<รหัส>.csv` เช่น `S50Z26.csv`
คอลัมน์ `date, open, high, low, close, volume, open_interest` (open_interest ว่างได้ จะ roll ตามวอลุ่มแทน)

ข้อมูลหนึ่งวันต่อหนึ่งแถว (ยกเว้นไฟล์รายกลุ่ม/รายตัวที่มีหลายแถวต่อวัน) · ห้ามมีวันซ้ำ · ระบบจะโยน error พร้อมบอกบรรทัดถ้าผิดรูป

`sample/` คือข้อมูล**จำลอง**ที่สร้างด้วย `python3 -m tfexflow synth` — ใช้ทดสอบโปรแกรมเท่านั้น
