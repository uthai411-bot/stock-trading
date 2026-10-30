"""รูปแบบไฟล์ CSV ที่ระบบรับ — ตรวจตั้งแต่ประตูเข้า จะได้ไม่ต้องไล่หาที่หลังว่าคอลัมน์ไหนหาย

ข้อความ error เป็นภาษาไทยและบอกว่าไฟล์ไหน คอลัมน์ไหน บรรทัดไหน — คนวางไฟล์ต้องแก้เองได้
"""
from dataclasses import dataclass

import pandas as pd


class DataFormatError(ValueError):
    pass


@dataclass(frozen=True)
class Schema:
    filename: str
    required: tuple[str, ...]
    key: tuple[str, ...]          # คอลัมน์ที่รวมกันแล้วห้ามซ้ำ
    numeric: tuple[str, ...]
    categories: dict[str, tuple[str, ...]] | None = None
    optional: bool = False


S50_DAILY = Schema(
    filename="s50_daily.csv",
    required=("date", "open", "high", "low", "close", "volume", "open_interest"),
    key=("date",),
    numeric=("open", "high", "low", "close", "volume", "open_interest"),
)
SET50_INDEX = Schema(
    filename="set50_index_daily.csv",
    required=("date", "close"),
    key=("date",),
    numeric=("close",),
)
SET_INVESTOR = Schema(
    filename="set_investor_daily.csv",
    required=("date", "investor_type", "buy_value", "sell_value"),
    key=("date", "investor_type"),
    numeric=("buy_value", "sell_value"),
    categories={"investor_type": ("foreign", "institution", "proprietary", "retail")},
)
TFEX_INVESTOR = Schema(
    filename="tfex_investor_daily.csv",
    required=("date", "investor_type", "long_contracts", "short_contracts"),
    key=("date", "investor_type"),
    numeric=("long_contracts", "short_contracts"),
    categories={"investor_type": ("foreign", "institution", "local")},
    optional=True,
)
CONSTITUENTS = Schema(
    filename="constituents_daily.csv",
    required=("date", "symbol", "close", "volume", "weight"),
    key=("date", "symbol"),
    numeric=("close", "volume", "weight"),
    optional=True,
)

ALL_SCHEMAS = (S50_DAILY, SET50_INDEX, SET_INVESTOR, TFEX_INVESTOR, CONSTITUENTS)


def validate(df: pd.DataFrame, schema: Schema) -> pd.DataFrame:
    """ตรวจและแปลงชนิดข้อมูล · คืน DataFrame ที่เรียงตามวันแล้ว"""
    missing = [c for c in schema.required if c not in df.columns]
    if missing:
        raise DataFormatError(
            f"ไฟล์ {schema.filename} ขาดคอลัมน์ {', '.join(missing)} — "
            f"ต้องมีคอลัมน์ {', '.join(schema.required)}"
        )
    out = df.copy()
    try:
        out["date"] = pd.to_datetime(out["date"], format="%Y-%m-%d")
    except (ValueError, TypeError) as e:
        raise DataFormatError(
            f"ไฟล์ {schema.filename} คอลัมน์ date ต้องเป็น YYYY-MM-DD (ค.ศ.) — {e}"
        ) from e
    for col in schema.numeric:
        converted = pd.to_numeric(out[col], errors="coerce")
        bad = out.index[converted.isna() & out[col].notna()]
        if len(bad):
            row = int(bad[0]) + 2  # +1 header +1 index เริ่มที่ 0
            raise DataFormatError(
                f"ไฟล์ {schema.filename} คอลัมน์ {col} บรรทัดที่ {row} ไม่ใช่ตัวเลข: {out[col].iloc[bad[0]]!r}"
            )
        out[col] = converted.astype(float)
    if schema.categories:
        for col, allowed in schema.categories.items():
            out[col] = out[col].astype(str).str.strip().str.lower()
            unknown = sorted(set(out[col]) - set(allowed))
            if unknown:
                raise DataFormatError(
                    f"ไฟล์ {schema.filename} คอลัมน์ {col} มีค่าที่ไม่รู้จัก {unknown} — "
                    f"ใช้ได้เฉพาะ {', '.join(allowed)}"
                )
    dup = out.duplicated(subset=list(schema.key), keep=False)
    if dup.any():
        first = out.loc[dup].iloc[0]
        keyval = ", ".join(f"{k}={first[k].date() if k == 'date' else first[k]}" for k in schema.key)
        raise DataFormatError(f"ไฟล์ {schema.filename} มีแถวซ้ำ ({keyval}) — หนึ่งค่าต่อหนึ่งแถวเท่านั้น")
    return out.sort_values(list(schema.key)).reset_index(drop=True)
