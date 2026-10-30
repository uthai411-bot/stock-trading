"""โหลดไฟล์จากโฟลเดอร์ข้อมูล → Dataset ที่ตรวจแล้ว"""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import schemas as S


@dataclass
class Dataset:
    s50: pd.DataFrame                       # date-indexed OHLCV + open_interest
    index: pd.DataFrame                     # date-indexed close
    set_investor: pd.DataFrame              # wide: date index · columns <type>_net (ล้านบาท)
    tfex_investor: pd.DataFrame | None      # wide: date index · columns <type>_net (สัญญา)
    constituents: pd.DataFrame | None       # long: date, symbol, close, volume, weight
    source: str

    @property
    def available(self) -> dict[str, bool]:
        return {
            "tfex_investor": self.tfex_investor is not None,
            "constituents": self.constituents is not None,
        }


def _read(folder: Path, schema: S.Schema) -> pd.DataFrame | None:
    path = folder / schema.filename
    if not path.exists():
        if schema.optional:
            return None
        raise S.DataFormatError(
            f"ไม่พบไฟล์ {schema.filename} ในโฟลเดอร์ {folder} — ไฟล์นี้จำเป็น (ดู data/README.md)"
        )
    return S.validate(pd.read_csv(path), schema)


def _pivot_net(df: pd.DataFrame, buy: str, sell: str) -> pd.DataFrame:
    """long → wide ของยอดสุทธิรายกลุ่ม · คอลัมน์ <type>_net"""
    net = df.assign(net=df[buy] - df[sell]).pivot(index="date", columns="investor_type", values="net")
    net.columns = [f"{c}_net" for c in net.columns]
    return net.sort_index()


def load(folder: str | Path) -> Dataset:
    folder = Path(folder)
    s50 = _read(folder, S.S50_DAILY).set_index("date")
    index = _read(folder, S.SET50_INDEX).set_index("date")
    set_inv = _pivot_net(_read(folder, S.SET_INVESTOR), "buy_value", "sell_value")
    tfex_raw = _read(folder, S.TFEX_INVESTOR)
    tfex_inv = _pivot_net(tfex_raw, "long_contracts", "short_contracts") if tfex_raw is not None else None
    cons = _read(folder, S.CONSTITUENTS)

    # ★ จัดทุกชุดให้อยู่บนปฏิทินของ S50 — วันที่ TFEX เปิดแต่ตลาดหุ้นปิด (เกิดได้) ให้ ffill ปัจจัยหุ้น
    cal = s50.index
    index = index.reindex(cal).ffill()
    set_inv = set_inv.reindex(cal).fillna(0.0)
    if tfex_inv is not None:
        tfex_inv = tfex_inv.reindex(cal).fillna(0.0)
    return Dataset(s50=s50, index=index, set_investor=set_inv, tfex_investor=tfex_inv,
                   constituents=cons, source=str(folder))
