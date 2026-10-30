"""ดึงแท่งเทียนรายวันจาก Settrade Open API (อ่านอย่างเดียว)

★★★ โมดูลนี้ใช้เฉพาะ `Investor.MarketData()` — **ห้าม** เรียก `Derivatives()` / `Equity()` ที่นี่
เพราะสองตัวนั้นส่งคำสั่งซื้อขายได้ (place_order) · ตามแผนที่ตกลง การส่งคำสั่งยังไม่ถึงเวลา
มีเทสต์ไล่อ่านไฟล์นี้กันไว้ (`test_settrade_ไม่แตะโมดูลส่งคำสั่ง`)

ต้องติดตั้ง SDK ทางการก่อนใช้:  pip install settrade-v2
ค่าที่ต้องตั้งใน .env (ได้จาก developer.settrade.com หลังโบรกเกอร์อนุมัติ):
  SETTRADE_APP_ID · SETTRADE_APP_SECRET · SETTRADE_APP_CODE · SETTRADE_BROKER_ID
  (ทดสอบด้วย sandbox: SETTRADE_BROKER_ID=SANDBOX)

ข้อจำกัดที่รู้แล้วจากการอ่านโค้ด SDK 2.2.1: แท่งเทียนไม่มี Open Interest
⇒ ไฟล์ซีรีส์ที่ได้จากที่นี่มี open_interest ว่าง · roll จะใช้วอลุ่มแทน · ปัจจัย OI regime จะเป็นศูนย์
   ถ้าต้องการ OI ให้ใช้ไฟล์ Export รายซีรีส์จากเว็บ TFEX แทน
"""
import os
from datetime import datetime, timezone

import pandas as pd

REQUIRED_ENV = ("SETTRADE_APP_ID", "SETTRADE_APP_SECRET", "SETTRADE_APP_CODE", "SETTRADE_BROKER_ID")
BKK = "Asia/Bangkok"


class SettradeConfigError(RuntimeError):
    pass


def market_from_env():
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        raise SettradeConfigError(
            f"ยังไม่ได้ตั้งค่า {', '.join(missing)} ในไฟล์ .env — ดูวิธีขอได้ที่ docs/data-sources.md")
    try:
        from settrade_v2 import Investor  # import ตอนใช้เท่านั้น — ไม่บังคับติดตั้งสำหรับคนที่ใช้ไฟล์ CSV
    except ImportError as e:
        raise SettradeConfigError("ยังไม่ได้ติดตั้ง SDK ของ Settrade — รัน: pip install settrade-v2") from e
    inv = Investor(app_id=os.environ["SETTRADE_APP_ID"], app_secret=os.environ["SETTRADE_APP_SECRET"],
                   app_code=os.environ["SETTRADE_APP_CODE"], broker_id=os.environ["SETTRADE_BROKER_ID"],
                   is_auto_queue=False)
    return inv.MarketData()


def _to_date(t) -> pd.Timestamp:
    if isinstance(t, (int, float)):
        ts = datetime.fromtimestamp(t / 1000 if t > 1e11 else t, tz=timezone.utc)
        return pd.Timestamp(ts).tz_convert(BKK).tz_localize(None).normalize()
    return pd.Timestamp(t).tz_localize(None).normalize() if pd.Timestamp(t).tzinfo else pd.Timestamp(t).normalize()


def candles_to_frame(resp) -> pd.DataFrame:
    """รับคำตอบได้ทั้งแบบ dict ของ list ({'time': [...], 'open': [...]}) และ list ของ dict"""
    if isinstance(resp, dict) and "time" in resp:
        df = pd.DataFrame({k: resp[k] for k in ("time", "open", "high", "low", "close", "volume") if k in resp})
    elif isinstance(resp, list):
        df = pd.DataFrame(resp)
    else:
        keys = list(resp)[:8] if isinstance(resp, dict) else type(resp).__name__
        raise ValueError(f"รูปแบบคำตอบแท่งเทียนจาก Settrade ไม่ตรงที่รู้จัก (คีย์: {keys}) — ต้องปรับตัวแปลง")
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]).rename_axis("date")
    df["date"] = [_to_date(t) for t in df["time"]]
    out = df.drop(columns=["time"]).groupby("date").last().sort_index()
    return out[["open", "high", "low", "close", "volume"]].astype(float)


def fetch_daily(market, symbol: str, start: str, end: str) -> pd.DataFrame:
    """start/end = 'YYYY-MM-DD' · ส่งต่อให้ SDK ในรูปแบบ ISO"""
    resp = market.get_candlestick(symbol=symbol, interval="1d", start=f"{start}T00:00", end=f"{end}T23:59")
    return candles_to_frame(resp)
