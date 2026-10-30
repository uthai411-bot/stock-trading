# TFEX Flow — ระบบวิเคราะห์กระแสเงินเพื่อหาจุดซื้อขาย S50 Futures

> โปรเจกต์นี้ **แยกจาก SAMUD โดยสิ้นเชิง** — อยู่ในโฟลเดอร์นี้ชั่วคราวเพื่อให้เปิดดูได้จากแอป
> ควรย้ายไป repository ของตัวเองเมื่อเริ่มใช้งานจริง · กติกาใน `CLAUDE.md` ของ SAMUD ไม่ครอบคลุมโฟลเดอร์นี้

## สมมุติฐานที่ระบบนี้สร้างมาเพื่อ "พิสูจน์" ไม่ใช่ "เชื่อ"

กระแสเงินของผู้ลงทุนรายกลุ่ม (ต่างชาติ · สถาบัน · บัญชีบริษัทหลักทรัพย์ · รายย่อย) ทั้งในตลาดหุ้น
และใน TFEX รวมกับวอลุ่มของหุ้น 50 ตัวในดัชนี มีอำนาจทำนายทิศทาง S50 Futures ในวันถัดไป
มากพอที่จะชนะต้นทุนการซื้อขาย

⇒ ขั้นแรกของระบบคือ **`hypothesis`** — วัดอำนาจทำนายด้วยตัวเลขก่อนเชื่อ · ถ้าตัวเลขอ่อน ไม่ต้องสร้างต่อ

## โครงสร้าง

```
tfexflow/
  config.py              สเปกสัญญา S50 · ต้นทุน · น้ำหนักสัญญาณ · เกณฑ์ตัดสิน  ← แก้ค่าที่นี่ที่เดียว
  data/schemas.py        รูปแบบไฟล์ CSV ที่ระบบรับ (ตรวจคอลัมน์ · ชนิด · วันที่ซ้ำ)
  data/loaders.py        โหลดไฟล์จากโฟลเดอร์ข้อมูล → DataFrame ที่ตรวจแล้ว
  data/synthetic.py      ★ ข้อมูลจำลองสำหรับพัฒนา/ทดสอบ — ไม่ใช่ข้อมูลจริง
  features/flow.py       กระแสเงินรายกลุ่มในตลาดหุ้น → z-score สะสม 5/20 วัน
  features/futures.py    TFEX: สถานะสุทธิรายกลุ่ม · OI regime · basis เทียบมูลค่ายุติธรรม
  features/breadth.py    หุ้น 50 ตัว: breadth · money flow ถ่วงน้ำหนัก
  features/trend.py      EMA · ATR บน S50
  signals/composite.py   รวมทุกปัจจัยเป็นคะแนนเดียว → LONG / SHORT / FLAT
  research/hypothesis.py ★ วัดอำนาจทำนาย (IC · t-stat · quintile) ของแต่ละปัจจัยต่อผลตอบแทนล่วงหน้า
  backtest/engine.py     ทดสอบย้อนหลังรายวัน · ต้นทุนจริง · ขนาดสถานะตาม ATR · สวิตช์ตัดขาดทุน · walk-forward
  backtest/metrics.py    Sharpe · max drawdown · profit factor · จำนวนรอบ
  report/html.py         แดชบอร์ด HTML ไฟล์เดียว (SVG ในตัว ไม่พึ่งไลบรารีภายนอก)
  cli.py                 คำสั่ง: synth · hypothesis · backtest · signal · report
tests/                   pytest
data/                    วางไฟล์ CSV จริงที่นี่ (ดู data/README.md) · data/sample = จำลอง
out/                     ผลลัพธ์ (signal.json · report.html · backtest.csv)
```

## หลักการที่ห้ามละเมิด

1. **ไม่มองอนาคต** — ปัจจัยที่คำนวณ ณ วันปิด t ใช้ตัดสินใจได้เร็วสุดที่ราคาเปิดวัน t+1
   ข้อมูลผู้ลงทุนรายกลุ่มเผยแพร่หลังตลาดปิด จึงเป็นข้อมูลของวัน t ที่ "รู้" ตอนเย็นวัน t
2. **ต้นทุนเข้าทุกรอบ** — ค่าคอม + VAT + slippage ทั้งขาเข้าและขาออก (`config.py`)
3. **ทดสอบแบบ walk-forward** — เลือกพารามิเตอร์จากช่วงฝึก ใช้กับช่วงทดสอบที่ไม่เคยเห็น
4. **ข้อมูลจำลองใช้พัฒนาเท่านั้น** — ผลจาก `data/sample` ไม่มีความหมายต่อการตัดสินใจลงทุน

## ใช้งาน

```bash
cd tfex-flow
python3 -m pytest -q                                   # เทสต์ทั้งหมด
python3 -m tfexflow synth      --out data/sample       # สร้างข้อมูลจำลอง 3 ปี
python3 -m tfexflow hypothesis --data data/sample      # ขั้นที่ 1: วัดอำนาจทำนาย
python3 -m tfexflow backtest   --data data/sample      # ขั้นที่ 2: ทดสอบย้อนหลัง + walk-forward
python3 -m tfexflow signal     --data data/sample      # สัญญาณของวันถัดไป → out/signal.json
python3 -m tfexflow report     --data data/sample      # แดชบอร์ด → out/report.html
```

## แผนขั้นถัดไป (ยังไม่ทำ)

- ดึงข้อมูลจริงอัตโนมัติ (SET investor type · TFEX investor type · หุ้น SET50) — รอยืนยันแหล่งข้อมูลที่ใช้
- ชั้นรายนาที: volume delta จาก tick ผ่าน Settrade Open API — ทำหลังสัญญาณรายวันพิสูจน์แล้ว
- ส่งคำสั่งจริง — ทำหลังเทรดด้วยมือตามสัญญาณอย่างน้อย 1 ไตรมาส
