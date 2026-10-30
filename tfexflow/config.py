"""ค่าคงที่ทั้งหมดของระบบ — แก้ที่นี่ที่เดียว ห้ามฝังตัวเลขในโมดูลอื่น

ทำไมต้องรวมไว้ที่เดียว: ต้นทุนและน้ำหนักสัญญาณคือสิ่งที่เปลี่ยนผลทดสอบย้อนหลังได้มากที่สุด
ถ้ากระจายอยู่หลายไฟล์ จะมีวันที่ค่าในทดสอบกับค่าในสัญญาณจริงไม่ตรงกันโดยไม่มีใครรู้
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContractSpec:
    """สเปก S50 Futures ของ TFEX"""
    symbol: str = "S50"
    point_value_thb: float = 200.0      # 1 จุดดัชนี = 200 บาท
    tick_size: float = 0.1
    trading_days_per_year: int = 245    # วันทำการ TFEX โดยประมาณ (ใช้ annualize Sharpe)


@dataclass(frozen=True)
class CostModel:
    """ต้นทุนต่อสัญญาต่อข้าง (เข้า 1 ครั้ง · ออก 1 ครั้ง = 2 ข้าง)

    ค่าคอมของโบรกเกอร์รายย่อยสำหรับ S50 อยู่ราว 40–90 บาท/สัญญา/ข้าง ก่อน VAT
    ตั้งค่าเริ่มต้นไว้กลาง ๆ · slippage 0.2 จุด = 40 บาท ถือว่าสมเหตุสมผลสำหรับสัญญาใกล้สุดช่วงปกติ
    """
    commission_thb: float = 45.0
    vat_rate: float = 0.07
    slippage_points: float = 0.2

    def per_side_thb(self, spec: ContractSpec = ContractSpec()) -> float:
        return self.commission_thb * (1 + self.vat_rate) + self.slippage_points * spec.point_value_thb

    def round_trip_thb(self, spec: ContractSpec = ContractSpec()) -> float:
        return 2 * self.per_side_thb(spec)

    def round_trip_points(self, spec: ContractSpec = ContractSpec()) -> float:
        return self.round_trip_thb(spec) / spec.point_value_thb


@dataclass(frozen=True)
class FeatureParams:
    """หน้าต่างคำนวณปัจจัย — ทุกค่าเป็น "วันทำการ" """
    flow_short: int = 5
    flow_long: int = 20
    zscore_window: int = 250       # ประมาณ 1 ปี สำหรับทำ z-score ของยอดสะสม
    basis_window: int = 60
    ema_fast: int = 20
    ema_slow: int = 50
    atr_window: int = 14
    breadth_ema: int = 20


@dataclass(frozen=True)
class SignalWeights:
    """น้ำหนักของแต่ละปัจจัยในคะแนนรวม — ค่าเริ่มต้นนี้ **ยังไม่ได้มาจากข้อมูลจริง**

    ★ ต้องปรับหลังรัน `hypothesis` กับข้อมูลจริง: ปัจจัยที่ IC ไม่ต่างจากศูนย์ให้ตั้งน้ำหนัก 0
    ปัจจัยที่ไม่มีไฟล์ข้อมูล ระบบจะตัดออกและ normalize น้ำหนักที่เหลือให้รวมเป็น 1 เอง
    """
    set_foreign_flow: float = 0.30     # ยอดซื้อสุทธิต่างชาติในตลาดหุ้น (z-score 5 วัน)
    set_institution_flow: float = 0.10
    tfex_foreign_position: float = 0.25  # การเปลี่ยนสถานะสุทธิต่างชาติใน S50
    oi_regime: float = 0.10
    basis: float = 0.05
    breadth: float = 0.10
    money_flow: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.__dict__.items()}


@dataclass(frozen=True)
class SignalRules:
    """เกณฑ์แปลงคะแนนเป็นสถานะ"""
    long_threshold: float = 0.30
    short_threshold: float = -0.30
    trend_filter: bool = True      # LONG ได้เมื่อปิดเหนือ EMA ช้า · SHORT ได้เมื่อปิดต่ำกว่า
    min_hold_days: int = 1         # ถือขั้นต่ำกี่วันก่อนกลับสถานะ (ลดการเทรดถี่เพราะเสียงรบกวน)


@dataclass(frozen=True)
class RiskRules:
    """กฎบริหารความเสี่ยงที่ระบบอัตโนมัติต้องมี — ไม่ใช่ตัวเลือก"""
    capital_thb: float = 1_000_000.0
    risk_per_trade_pct: float = 0.01     # เสี่ยง 1% ของทุนต่อรอบ (ใช้ ATR กำหนดจำนวนสัญญา)
    atr_stop_multiple: float = 2.0       # หยุดขาดทุนที่ 2 ATR
    max_contracts: int = 10
    max_drawdown_pct: float = 0.15       # ★ สวิตช์ตัด: ถ้าขาดทุนจากจุดสูงสุดเกิน 15% หยุดเทรด
    cooldown_days: int = 10              # หยุดกี่วันหลังสวิตช์ตัดทำงาน
    daily_loss_limit_pct: float = 0.03   # ขาดทุนวันเดียวเกิน 3% → ปิดสถานะและหยุดวันนั้น


@dataclass(frozen=True)
class Settings:
    spec: ContractSpec = field(default_factory=ContractSpec)
    cost: CostModel = field(default_factory=CostModel)
    features: FeatureParams = field(default_factory=FeatureParams)
    weights: SignalWeights = field(default_factory=SignalWeights)
    rules: SignalRules = field(default_factory=SignalRules)
    risk: RiskRules = field(default_factory=RiskRules)


DEFAULT = Settings()
