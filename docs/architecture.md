# สถาปัตยกรรม TFEX Flow

## ภาพรวม — ข้อมูลไหลทางเดียว

```
 แหล่งข้อมูล                     ingest/                 data/<ชุด>/*.csv        features/            signals/          ผลลัพธ์
 ─────────────────────────────   ─────────────────────   ─────────────────────   ──────────────────   ───────────────   ─────────────────
 Settrade Open API (แท่งเทียน) → fetch  → series/S50*.csv ┐
 เว็บ TFEX Export รายซีรีส์    ────────────────────────→ ├ roll → s50_daily.csv ┐
 Settrade (ดัชนี SET50)        → fetch ──────────────────────→ set50_index_daily ├→ build_features → composite → state ─┬→ signal.json
 เว็บ SET / TFEX (ยอดรายกลุ่ม) → add-flow (กรอกมือ) ───────→ *_investor_daily   │   (ปัจจัย f_*)      (คะแนน)  (L/S/F) ├→ report.html
 SETSMART (ยอดรายกลุ่มย้อนหลัง) → (ตัวแปลง — รอเห็นไฟล์จริง) → *_investor_daily  │                                     └→ backtest / walk-forward
 หุ้น SET50 รายตัว              → (ตัวแปลง — รอเห็นไฟล์จริง) → constituents_daily ┘                  research/hypothesis → น้ำหนักใน config.py
```

★ ทุกทางเข้าจบที่ไฟล์ CSV กลาง แล้วผ่านด่านตรวจเดียวกัน (`data/schemas.py`) — สลับแหล่งข้อมูลได้โดยไม่แตะส่วนวิเคราะห์

## ชั้นและหน้าที่

| ชั้น | โมดูล | หน้าที่ | ห้าม |
|---|---|---|---|
| นำเข้า | `ingest/settrade.py` | ดึงแท่งเทียนรายวัน S50 ทุกซีรีส์ + ดัชนี SET50 | เรียก `Derivatives()` `Equity()` `place_order` (มีเทสต์กัน) |
| | `ingest/roll.py` | ต่อซีรีส์เป็นเส้นต่อเนื่อง · roll ตาม OI (หรือวอลุ่ม) · ปรับราคาย้อนหลัง | ต่อราคาดิบ (เกิดกำไรปลอมวัน roll) |
| | `ingest/flowlog.py` | กรอกยอดรายกลุ่มวันละครั้ง · กันวันซ้ำ · ตรวจผลรวมสุทธิเป็นศูนย์ | เขียนทับวันเดิมเงียบ ๆ |
| ข้อมูล | `data/schemas.py` `loaders.py` | ตรวจรูปแบบ · จัดทุกชุดบนปฏิทินของ S50 | |
| ปัจจัย | `features/*` | คำนวณปัจจัยรายวัน → normalize เป็น −1…+1 (คอลัมน์ `f_*`) | ใช้ข้อมูลหลังปิดวัน t ในแถววัน t |
| สัญญาณ | `signals/composite.py` | ถ่วงน้ำหนัก → คะแนน → LONG/SHORT/FLAT + ตัวกรองแนวโน้ม | |
| วิจัย | `research/hypothesis.py` | IC · t-stat · quintile spread หลังต้นทุน → คำตัดสินต่อปัจจัย | |
| ทดสอบ | `backtest/*` | เข้า open วันถัดไป · ต้นทุนสองข้าง · stop · สวิตช์ตัด · walk-forward | |
| แสดงผล | `report/html.py` | แดชบอร์ดไฟล์เดียว อธิบายที่มาของคะแนน | โหลดสคริปต์จากภายนอก |

## งานประจำวัน (เมื่อมีข้อมูลจริงแล้ว) — หลังตลาดปิด ~18:00

```bash
python3 -m tfexflow fetch    --start <วันแรกของเดือนก่อน> --end <วันนี้> --out data/real
python3 -m tfexflow roll     --series-dir data/real/series --out data/real
python3 -m tfexflow add-flow set  --date <วันนี้> --data data/real --foreign ซื้อ/ขาย --institution ซื้อ/ขาย --proprietary ซื้อ/ขาย --retail ซื้อ/ขาย
python3 -m tfexflow add-flow tfex --date <วันนี้> --data data/real --foreign ยาว/สั้น --institution ยาว/สั้น --local ยาว/สั้น
python3 -m tfexflow signal   --data data/real      # → out/signal.json (ใช้กับราคาเปิดพรุ่งนี้)
python3 -m tfexflow report   --data data/real      # → out/report.html
```

## เส้นทางพัฒนา (ตามลำดับที่ตกลงกับเจ้าของ — ห้ามข้ามขั้น)

| ขั้น | สิ่งที่ต้องมี | ประตูผ่าน | สถานะ |
|---|---|---|---|
| 0 | โครงระบบ + เทสต์บนข้อมูลจำลอง | เทสต์เขียว · สมมุติฐานว่างผ่าน | ✅ |
| 1 | ชั้นนำเข้า: Settrade · roll · กรอกมือ | เทสต์เขียว | ✅ (ตัวแปลง SETSMART รอไฟล์จริง) |
| 2 | ข้อมูลจริง ≥ 3 ปี → `hypothesis` | มีปัจจัยอย่างน้อยหนึ่งตัว \|t\| ≥ 2 และ spread หลังต้นทุน > 0 | ☐ รอสมัครแหล่งข้อมูล |
| 3 | ตั้งน้ำหนักจากขั้น 2 → walk-forward | Sharpe นอกตัวอย่าง > 0.5 · max DD < 15% · ≥ 200 รอบ | ☐ |
| 4 | เทรดมือตาม `signal.json` 1 ไตรมาส + จดบันทึก | ผลจริงไม่ต่างจาก walk-forward อย่างมีนัย | ☐ |
| 5 | กึ่งอัตโนมัติ: ระบบเตือน คนกดยืนยัน | | ☐ ต้องขออนุมัติเจ้าของ |
| 6 | อัตโนมัติ + สวิตช์ตัด + จำกัดขาดทุนรายวัน | | ☐ ต้องขออนุมัติเจ้าของ |
| — | ชั้นรายนาที (volume delta จาก tick) | หลังขั้น 3 ผ่าน | ☐ |

## การตัดสินใจที่บันทึกไว้

- **ไฟล์ CSV เป็นตัวกลาง ไม่ใช่ฐานข้อมูล** — ข้อมูลรายวัน 50 หุ้น × 5 ปี ≈ 60,000 แถว pandas อ่านไม่ถึงวินาที
  ย้ายไป Postgres/TimescaleDB เมื่อเริ่มชั้นรายนาที
- **Open Interest มาจากเว็บ TFEX ไม่ใช่ Settrade** — อ่านโค้ด SDK `settrade-v2` 2.2.1 แล้ว แท่งเทียนไม่มี OI
- **SDK ของ Settrade เป็น optional** — import ตอนใช้คำสั่ง `fetch` เท่านั้น · ยังไม่อยู่ใน requirements.txt
  (รอเจ้าของอนุมัติตาม CLAUDE.md ข้อ 6 · SDK พ่วง requests cryptography betterproto paho-mqtt ntplib)
- **วันหยุดตลาดไทยยังไม่อยู่ในระบบ** — มีผลแค่การคาดวันหมดอายุซีรีส์ (ใช้วางแผนดึงข้อมูล) · การ roll ใช้ข้อมูลจริง
