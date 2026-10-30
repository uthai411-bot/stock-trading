"""ต่อซีรีส์รายเดือนของ S50 เป็นเส้นต่อเนื่อง (continuous) สำหรับ s50_daily.csv

กติกา roll: ถือซีรีส์ใกล้สุด · ย้ายไปซีรีส์ถัดไปในวันแรกที่ OI (หรือวอลุ่มถ้าไม่มี OI) ของซีรีส์ถัดไป
สูงกว่าซีรีส์ปัจจุบัน หรือเมื่อซีรีส์ปัจจุบันหมดข้อมูล · **ไม่ย้อนกลับ**

★★ ทำไมต้องปรับราคาย้อนหลัง (back-adjust): วันที่ roll ราคาสองซีรีส์ต่างกันเท่า basis
ถ้าต่อดิบ ๆ เครื่องทดสอบจะเห็น "กำไร/ขาดทุน" หลายจุดที่ไม่มีใครได้จริง
⇒ open/high/low/close = ราคาปรับย้อนหลังแบบบวกส่วนต่าง (ใช้คำนวณผลตอบแทนและสัญญาณ)
⇒ close_raw = ราคาจริงของซีรีส์ที่ถืออยู่ (ใช้คำนวณ basis เทียบดัชนี)
"""
import numpy as np
import pandas as pd

from . import series as S

PRICE_COLS = ("open", "high", "low", "close")


def _rank_value(df: pd.DataFrame) -> pd.Series:
    oi = df.get("open_interest")
    if oi is not None and oi.notna().any() and (oi.fillna(0) > 0).any():
        return oi.fillna(0)
    return df["volume"].fillna(0)


def build_continuous(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """frames: {'S50Z26': df(date-index, open, high, low, close, volume, open_interest?)}"""
    if not frames:
        raise ValueError("ไม่มีไฟล์ซีรีส์ให้ต่อ — ต้องมีอย่างน้อยหนึ่งซีรีส์")
    codes = sorted(frames, key=lambda c: S.parse(c)[1:])
    calendar = sorted(set().union(*[f.index for f in frames.values()]))
    held_i = 0
    rows = []
    for d in calendar:
        # ข้ามซีรีส์ที่หมดอายุไปแล้ว (ไม่มีข้อมูลตั้งแต่วันนี้ไป)
        while held_i < len(codes) - 1 and frames[codes[held_i]].index.max() < d:
            held_i += 1
        cur = codes[held_i]
        if held_i < len(codes) - 1:
            nxt = codes[held_i + 1]
            fn, fc = frames[nxt], frames[cur]
            if d in fn.index and d in fc.index and _rank_value(fn).loc[d] > _rank_value(fc).loc[d]:
                held_i += 1
                cur = nxt
        f = frames[cur]
        if d not in f.index:
            continue
        r = f.loc[d]
        rows.append({"date": d, "series": cur, **{c: float(r[c]) for c in PRICE_COLS},
                     "volume": float(r["volume"]),
                     "open_interest": float(r["open_interest"]) if "open_interest" in f and pd.notna(r["open_interest"]) else np.nan})
    out = pd.DataFrame(rows).set_index("date")
    out["close_raw"] = out["close"]

    # back-adjust: วันที่เปลี่ยนซีรีส์ ส่วนต่าง = ราคาปิดซีรีส์ใหม่ − ราคาปิดซีรีส์เก่า ของ "วันก่อน roll"
    # แล้วบวกส่วนต่างนั้นให้ทุกแถวก่อนหน้า ⇒ ราคาล่าสุดเป็นราคาจริง ราคาเก่าเลื่อนตาม
    adj = np.zeros(len(out))
    ser = out["series"].to_numpy()
    for i in range(1, len(out)):
        if ser[i] != ser[i - 1]:
            prev_day = out.index[i - 1]
            new_f, old_f = frames[ser[i]], frames[ser[i - 1]]
            if prev_day in new_f.index:
                gap = float(new_f.loc[prev_day, "close"]) - float(old_f.loc[prev_day, "close"])
            else:  # ซีรีส์ใหม่ไม่มีข้อมูลวันก่อน — ใช้ open วันนี้เทียบ close เมื่อวาน (ประมาณ)
                gap = float(new_f.loc[out.index[i], "open"]) - float(old_f.loc[prev_day, "close"])
            adj[:i] += gap
    for c in PRICE_COLS:
        out[c] = out[c] + adj
    out["roll_adjustment"] = adj
    return out


def read_series_dir(folder) -> dict[str, pd.DataFrame]:
    """อ่านไฟล์ <รหัสซีรีส์>.csv ทุกไฟล์ในโฟลเดอร์ (เช่น S50Z26.csv) · คอลัมน์ date, open, high, low, close, volume[, open_interest]"""
    from pathlib import Path
    frames = {}
    for p in sorted(Path(folder).glob("*.csv")):
        try:
            S.parse(p.stem)
        except ValueError:
            continue
        df = pd.read_csv(p)
        missing = [c for c in ("date", *PRICE_COLS, "volume") if c not in df.columns]
        if missing:
            raise ValueError(f"ไฟล์ {p.name} ขาดคอลัมน์ {', '.join(missing)}")
        df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
        frames[p.stem.upper()] = df.set_index("date").sort_index()
    if not frames:
        raise ValueError(f"ไม่พบไฟล์ซีรีส์ (เช่น S50Z26.csv) ในโฟลเดอร์ {folder}")
    return frames


def write_s50_daily(cont: pd.DataFrame, path) -> None:
    cols = ["open", "high", "low", "close", "volume", "open_interest", "close_raw", "series", "roll_adjustment"]
    out = cont[cols].copy()
    out.index = out.index.strftime("%Y-%m-%d")
    out.index.name = "date"
    out.round(4).to_csv(path)
