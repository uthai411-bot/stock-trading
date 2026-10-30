# แหล่งข้อมูลที่ระบบต้องใช้ — ผลค้นหา 30 ต.ค. 2569

> ★ ค้นจากผลการค้นหาเว็บเท่านั้น — เซสชันที่ค้นเข้าเว็บ set.or.th และ tfex.co.th โดยตรงไม่ได้
> ราคาและเงื่อนไขทุกข้อ**ต้องยืนยันกับผู้ให้บริการก่อนจ่ายเงิน**

## สรุปสั้น — เส้นทางที่แนะนำ

| ลำดับ | สมัครอะไร | ได้อะไร | ค่าใช้จ่ายโดยประมาณ |
|---|---|---|---|
| 1 | **SETSMART** (setsmart.com) | ยอดซื้อขายรายกลุ่มผู้ลงทุน · ดัชนี SET50 · ราคา/วอลุ่มหุ้นรายตัว · ข้อมูล TFEX · **มี API สำหรับสมาชิก** (Tools → API Service) | แพ็กเกจเริ่มราว 250 บาท/เดือน (ประวัติ 3–5 ปีตามแพ็กเกจ) |
| 2 | **Settrade Open API** ผ่านโบรกเกอร์ที่มีบัญชี | แท่งเทียน S50 ย้อนหลัง (ถึงราย 1 นาที) · ข้อมูลเรียลไทม์ · **ส่งคำสั่ง TFEX** · มี sandbox · Python SDK | ฟรีเมื่อมีบัญชีกับโบรกเกอร์ที่ร่วม |
| 3 | (ถ้าต้องการย้อนหลังลึกกว่า 5 ปี) **SET Historical Data Request** | ไฟล์ส่งทางอีเมล · สถิติรายกลุ่มย้อนถึง 1975 · TFEX รายซีรีส์ตั้งแต่ เม.ย. 2006 | USD 160–200 ต่อ 1 ปีข้อมูล |

ข้อ 1 + 2 ครอบคลุมไฟล์ที่ระบบต้องการทั้ง 5 ไฟล์ · ข้อ 3 ซื้อเฉพาะเมื่อผล `hypothesis` บนข้อมูล 3–5 ปีบอกว่าคุ้มที่จะขยาย

## รายไฟล์

### 1. `set_investor_daily.csv` — ยอดซื้อขายรายกลุ่มในตลาดหุ้น

| แหล่ง | ลักษณะ | ประวัติ | ค่าใช้จ่าย | หมายเหตุ |
|---|---|---|---|---|
| หน้า Investor Type บน set.or.th (Market → Statistics) | ตารางเว็บ รายวัน/MTD/YTD แยก SET กับ mai 4 กลุ่ม | ดูย้อนได้จำกัด ไม่พบปุ่มดาวน์โหลด CSV จากผลค้นหา | ฟรี | เหมาะกับเก็บ "รายวันไปข้างหน้า" ไม่เหมาะดึงย้อนหลัง |
| **SETSMART** | เมนู Investor Type · ส่งออกได้ · API สำหรับสมาชิก | 3–5 ปีตามแพ็กเกจ | ~250 บาท/เดือนขึ้นไป | ★ ทางหลัก |
| SMART Marketplace ของ SET — ชุด Equity EOD (OAQ) | JSON API รวม "market trading by investor type" | ตามชุดข้อมูล | หน้าเว็บแสดงตัวเลข 5,000 บาท/เดือนแต่ตารางอ่านไม่ชัด — ถาม infoproducts@set.or.th | สำหรับองค์กร/นักพัฒนา |
| SET Historical Data Request | ไฟล์ทางอีเมลภายใน 7 วันทำการ | ย้อนถึง 1975 | USD 160 / 1 ปีข้อมูล | ใช้ภายในเท่านั้น |
| InfoQuest · Kaohoon (ข่าวสรุปรายวัน) | ข้อความ ไม่ใช่ตาราง | เฉพาะรายวัน | ฟรี | สำรองสำหรับ scrape รายวัน ไม่ใช่ประวัติ |

### 2. `tfex_investor_daily.csv` — ยอด long/short รายกลุ่มใน S50 Futures

| แหล่ง | ลักษณะ | หมายเหตุ |
|---|---|---|
| tfex.co.th → Market Data → Historical Data → **Trading Statistics by Investor Types** | ตารางเว็บ แยกสถาบันในประเทศ / ต่างชาติ / บุคคลในประเทศ · long/short/net หน่วยสัญญา · แยกตามสินค้า (Equity Index Futures) | ไม่ยืนยันว่ามีปุ่มส่งออก — ต้องเปิดดูเอง |
| SMART Marketplace — ชุด Derivatives EOD (ODQ) | JSON API รวม market trading by investor type ของ TFEX | ราคาไม่ปรากฏ ถาม SET |
| SETSMART | น่าจะมีในส่วน TFEX — ต้องยืนยันตอนสมัคร | |
| InfoQuest "TFEX สรุปปริมาณซื้อขายตามกลุ่มผู้ลงทุน" รายวัน | ข้อความ | สำรอง scrape รายวัน |

★ ตัวเลขของ TFEX เป็นระดับ "Equity Index Futures" ทั้งหมวด (S50 + S50 mini + รายหุ้น?) — ต้องตรวจว่าแยก S50 ได้ไหม ถ้าไม่ได้ให้ใช้ทั้งหมวดและบันทึกไว้

### 3. `s50_daily.csv` — S50 Futures รายวัน OHLCV + Open Interest

| แหล่ง | ลักษณะ | หมายเหตุ |
|---|---|---|
| tfex.co.th → หน้าสินค้าแต่ละซีรีส์ (เช่น S50Z26) → Historical Trading | มีปุ่ม Export ต่อซีรีส์ | ต้องโหลดทีละซีรีส์แล้ว **ต่อเป็นเส้นต่อเนื่อง** เอง (roll เมื่อ OI ซีรีส์ถัดไปสูงกว่า) — ระบบจะมีตัวต่อให้ |
| **Settrade Open API** — `get_candlestick` | ดึงได้ด้วยโค้ด ราย 1 นาทีถึงรายวัน | ต้องยืนยันความลึกของประวัติกับโบรกเกอร์ |
| TradingView สัญลักษณ์ `TFEX:S501!` | เส้นต่อเนื่องสำเร็จรูป | ส่งออก CSV ต้องแพ็กเกจเสียเงิน |
| SET Historical Data Request — "EOD by series (TFEX)" | ตั้งแต่ เม.ย. 2006 | USD 200 / 1 ปีข้อมูล |

### 4. `set50_index_daily.csv` — ดัชนี SET50 ปิดรายวัน

Investing.com (ดาวน์โหลดฟรีเมื่อล็อกอิน) · SETSMART · Settrade Open API · หน้า set.or.th

### 5. `constituents_daily.csv` — หุ้น 50 ตัว ราคา/วอลุ่ม/น้ำหนัก

| ส่วน | แหล่ง | หมายเหตุ |
|---|---|---|
| รายชื่อหุ้นในดัชนี (ครึ่งปี) | SET เผยแพร่ PDF ทุกครึ่งปี (ฟรี) | ไม่มีน้ำหนัก |
| **น้ำหนักในดัชนี** | SET ระบุ "contact Sale team" — ข้อมูลเสียเงิน | ★ ถ้าไม่มี ระบบถ่วงเท่ากันหรือใช้ market cap × free float ประมาณเอาได้ |
| ราคา/วอลุ่มรายตัว | SiamChart (ฟรี ต้องลงทะเบียน) · SETSMART · Settrade Open API | |

## Settrade Open API — ใช้ทั้งดึงข้อมูลและส่งคำสั่งในขั้นหลัง

- ลงทะเบียนที่ developer.settrade.com ผ่านโบรกเกอร์ที่มีบัญชีอยู่ (ได้ app id + secret)
- Python SDK ติดตั้งด้วย pip · ตัวอย่างทางการที่ github.com/settrade/stt-open-api-sdk-example (Python · Excel · AmiBroker)
- มี sandbox สำหรับทดสอบส่งคำสั่งโดยไม่ใช้เงินจริง — ตรงกับแผนขั้นที่ 4 (กึ่งอัตโนมัติ) และ 5
- ★ ข้อมูลเรียลไทม์และ API ต้องมีบัญชีกับโบรกเกอร์ที่เข้าร่วม — ถามโบรกเกอร์ของคุณก่อนว่ารองรับไหม

## สิ่งที่ยังไม่รู้ ต้องถามตอนสมัคร

1. SETSMART แพ็กเกจไหนมี Investor Type **รายวันย้อนหลัง** และมีข้อมูล TFEX รายกลุ่มด้วยไหม
2. หน้า Trading by Investor Types ของ TFEX ส่งออกเป็นไฟล์ได้ไหม และแยก S50 จาก Equity Index Futures ทั้งหมวดได้ไหม
3. Settrade Open API ให้แท่งเทียน S50 ย้อนหลังได้กี่ปี
4. น้ำหนัก SET50 รายวันราคาเท่าไร หรือจะใช้ค่าประมาณจาก market cap แทน

## อ้างอิง (จากผลค้นหา)

- https://www.tfex.co.th/en/market-data/historical-data/trading-by-investor-types
- https://www.tfex.co.th/en/market-data/historical-data/market-statistics
- https://www.set.or.th/en/market/statistics/market-statistics/trading-statistics
- https://classic.set.or.th/mkt/investortype.do?language=en&country=US/
- https://set.or.th/en/services/connectivity-and-data/data/smart-marketplace
- https://set.or.th/en/services/connectivity-and-data/data/web-based
- https://www.set.or.th/en/services/connectivity-and-data/data/historical
- https://www.set.or.th/app/online-data/oaq-data?lang=en
- https://developer.settrade.com/open-api/
- https://github.com/settrade/stt-open-api-sdk-example
- https://www.investing.com/indices/set-50-historical-data
- http://siamchart.com/download.php
- https://www.tradingview.com/symbols/TFEX-S501!/
- https://www.infoquest.co.th/2026/671354 (ตัวอย่างสรุป TFEX รายกลุ่ม 29 ต.ค. 69)
- https://kaohooninternational.com/markets/593505 (ตัวอย่างสรุป SET รายกลุ่ม 29 ต.ค. 69)
