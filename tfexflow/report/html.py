"""แดชบอร์ด HTML ไฟล์เดียว — SVG วาดเอง ไม่โหลดอะไรจากอินเทอร์เน็ต เปิดได้แม้ไม่มีเน็ต

เจตนา: ให้คนเห็น "คะแนนรวมวันนี้มาจากอะไร" ก่อนเห็นว่าระบบบอก LONG หรือ SHORT
เพราะสัญญาณที่อธิบายไม่ได้คือสัญญาณที่คนจะเลิกเชื่อหลังขาดทุนสองรอบแรก
"""
from html import escape

import numpy as np
import pandas as pd

from ..signals.composite import state_label

FACTOR_TH = {
    "set_foreign_flow": "ต่างชาติซื้อสุทธิ (หุ้น) 5 วัน",
    "set_institution_flow": "สถาบันซื้อสุทธิ (หุ้น) 5 วัน",
    "tfex_foreign_position": "ต่างชาติเพิ่มสถานะ S50 5 วัน",
    "oi_regime": "ราคา × Open Interest",
    "basis": "Basis เทียบปกติ (สวนทาง)",
    "breadth": "หุ้นใน 50 ตัวที่ยืนเหนือ EMA20",
    "money_flow": "Money flow ถ่วงน้ำหนัก 5 วัน",
}


def _svg_line(series: list[pd.Series], w=900, h=180, colors=("#2563eb", "#f59e0b", "#6b7280"),
              zero_line=False) -> str:
    df = pd.concat(series, axis=1).dropna(how="all")
    if df.empty:
        return "<svg></svg>"
    lo, hi = float(np.nanmin(df.to_numpy())), float(np.nanmax(df.to_numpy()))
    if zero_line:
        lo, hi = min(lo, 0), max(hi, 0)
    if hi == lo:
        hi = lo + 1
    pad = 8; n = len(df)
    def x(i): return pad + i * (w - 2 * pad) / max(1, n - 1)
    def y(v): return h - pad - (v - lo) * (h - 2 * pad) / (hi - lo)
    paths = []
    for k, col in enumerate(df.columns):
        pts = [f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(df[col].to_numpy()) if np.isfinite(v)]
        paths.append(f'<polyline fill="none" stroke="{colors[k % len(colors)]}" stroke-width="1.5" points="{" ".join(pts)}"/>')
    zl = f'<line x1="{pad}" x2="{w-pad}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="#9ca3af" stroke-dasharray="4 4"/>' if zero_line else ""
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="none">{zl}{"".join(paths)}'
            f'<text x="{pad}" y="14" font-size="11" fill="#6b7280">{hi:,.1f}</text>'
            f'<text x="{pad}" y="{h-2}" font-size="11" fill="#6b7280">{lo:,.1f}</text></svg>')


def _svg_bars(s: pd.Series, w=900, h=120) -> str:
    s = s.dropna()
    if s.empty:
        return "<svg></svg>"
    m = float(max(abs(s.min()), abs(s.max()))) or 1.0
    pad = 8; n = len(s); bw = max(1.0, (w - 2 * pad) / n)
    mid = h / 2
    bars = []
    for i, v in enumerate(s.to_numpy()):
        hh = abs(v) / m * (mid - pad)
        yy = mid - hh if v >= 0 else mid
        bars.append(f'<rect x="{pad + i*bw:.1f}" y="{yy:.1f}" width="{bw:.1f}" height="{hh:.1f}" fill="{"#16a34a" if v >= 0 else "#dc2626"}"/>')
    return f'<svg viewBox="0 0 {w} {h}" width="100%" preserveAspectRatio="none">{"".join(bars)}<line x1="{pad}" x2="{w-pad}" y1="{mid}" y2="{mid}" stroke="#9ca3af"/></svg>'


def _fmt(v, d=2):
    return "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:,.{d}f}"


def render(feats: pd.DataFrame, score: pd.Series, state: pd.Series, weights_used: dict[str, float],
           summary: dict | None, hypothesis: pd.DataFrame | None, source: str, lookback: int = 120,
           synthetic: bool = False) -> str:
    f = feats.tail(lookback); last = feats.index[-1]
    today_state = state_label(int(state.iloc[-1]))
    color = {"LONG": "#16a34a", "SHORT": "#dc2626", "FLAT": "#6b7280"}[today_state]

    contrib = []
    for k, w in sorted(weights_used.items(), key=lambda kv: -abs(kv[1])):
        v = float(feats[f"f_{k}"].iloc[-1]) if f"f_{k}" in feats else float("nan")
        contrib.append(f"<tr><td>{escape(FACTOR_TH.get(k, k))}</td><td class=r>{w:.0%}</td>"
                       f"<td class=r>{_fmt(v)}</td><td class=r><b>{_fmt(w*v if np.isfinite(v) else np.nan, 3)}</b></td></tr>")

    kpi = ""
    if summary:
        items = [("กำไรสุทธิ", f"{_fmt(summary['total_pnl_thb'],0)} ฿"), ("Sharpe", _fmt(summary["sharpe"])),
                 ("Max DD", f"{_fmt(summary['max_drawdown_pct'],1)}%"), ("Profit factor", _fmt(summary["profit_factor"])),
                 ("รอบ", str(summary["trades"])), ("ชนะ", f"{summary['win_rate']:.0%}"),
                 ("ต้นทุนรวม", f"{_fmt(summary['total_cost_thb'],0)} ฿"), ("สวิตช์ตัด", str(summary["kill_switch_triggers"]))]
        kpi = "".join(f"<div class=kpi><div class=k>{a}</div><div class=v>{b}</div></div>" for a, b in items)

    hyp = ""
    if hypothesis is not None and not hypothesis.empty:
        rows = "".join(
            f"<tr><td>{escape(FACTOR_TH.get(r.factor.replace('f_', ''), r.factor))}</td><td class=r>{r.horizon}</td>"
            f"<td class=r>{r.ic:+.3f}</td><td class=r>{r.t_stat:+.2f}</td><td class=r>{r.hit_rate:.0%}</td>"
            f"<td class=r>{r.spread_after_cost:+.1f}</td><td>{escape(r.verdict)}</td></tr>"
            for r in hypothesis.itertuples())
        hyp = f"""<section><h2>อำนาจทำนายของแต่ละปัจจัย (ขั้นที่ 1)</h2>
        <table><tr><th>ปัจจัย</th><th class=r>ระยะ (วัน)</th><th class=r>IC</th><th class=r>t-stat</th><th class=r>ทายถูก</th><th class=r>Q5−Q1 หลังต้นทุน (จุด)</th><th>คำตัดสิน</th></tr>{rows}</table>
        <p class=note>|t| ≥ 2 และ spread หลังต้นทุนเป็นบวก = น่าใช้ · |t| &lt; 1 = ไม่มีสัญญาณ ให้ตั้งน้ำหนัก 0</p></section>"""

    warn = ('<div class=warn>★ ข้อมูลจำลอง — ตัวเลขทุกตัวในหน้านี้ไม่มีความหมายต่อการลงทุนจริง</div>'
            if synthetic else "")
    eq = ""
    if summary and "equity" in feats.columns:
        eq = f"<section><h2>เส้นทุน (ทดสอบย้อนหลัง)</h2>{_svg_line([feats['equity'].rename('equity')])}</section>"

    tfex_block = ""
    if "tfex_foreign_pos" in f:
        tfex_block = f"<section><h2>สถานะสุทธิต่างชาติใน S50 (สะสม · สัญญา)</h2>{_svg_line([f['tfex_foreign_pos']], zero_line=True)}</section>"
    breadth_block = ""
    if "breadth_weighted" in f:
        breadth_block = f"<section><h2>Breadth ถ่วงน้ำหนัก (สัดส่วนหุ้นยืนเหนือ EMA20)</h2>{_svg_line([f['breadth_weighted']])}</section>"

    return f"""<!doctype html><html lang="th"><head><meta charset="utf-8"><title>TFEX Flow</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--bg:#fff;--fg:#111827;--mut:#6b7280;--card:#f9fafb;--line:#e5e7eb}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f172a;--fg:#e5e7eb;--mut:#94a3b8;--card:#1e293b;--line:#334155}}}}
body{{margin:0;padding:16px;font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans Thai",sans-serif;background:var(--bg);color:var(--fg);max-width:1000px;margin-inline:auto}}
h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:15px;margin:18px 0 8px;color:var(--mut);font-weight:600}}
.sub{{color:var(--mut);font-size:13px}} section{{margin-bottom:8px}}
.hero{{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:16px 0}}
.state{{font-size:40px;font-weight:800;color:{color};letter-spacing:1px}}
.score{{font-size:14px;color:var(--mut)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px}}
.kpi .k{{font-size:11px;color:var(--mut)}} .kpi .v{{font-size:16px;font-weight:700}}
table{{width:100%;border-collapse:collapse;font-size:13px}} td,th{{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}} .r{{text-align:right}}
.warn{{background:#fef3c7;color:#92400e;padding:8px 12px;border-radius:8px;font-size:13px;margin-bottom:12px}}
.note{{font-size:12px;color:var(--mut)}}
</style></head><body>
<h1>TFEX Flow — S50 Futures</h1>
<div class=sub>ข้อมูลถึง {last.date()} · แหล่ง {escape(source)} · สัญญาณนี้ใช้กับราคาเปิดวันทำการถัดไป</div>
{warn}
<div class=hero><div class=state>{today_state}</div><div class=score>คะแนนรวม {score.iloc[-1]:+.3f}<br>
เกณฑ์ LONG ≥ +0.30 · SHORT ≤ −0.30 · ปิด {_fmt(feats['close'].iloc[-1],1)} · EMA50 {_fmt(feats['ema_slow'].iloc[-1],1)} · ATR {_fmt(feats['atr'].iloc[-1],1)}</div></div>
<section><h2>คะแนนวันนี้มาจากอะไร</h2>
<table><tr><th>ปัจจัย</th><th class=r>น้ำหนัก</th><th class=r>ค่า (−1…+1)</th><th class=r>ส่วนร่วม</th></tr>{"".join(contrib)}</table></section>
<section><h2>S50 ปิด · EMA20 · EMA50 ({lookback} วัน)</h2>{_svg_line([f['close'], f['ema_fast'], f['ema_slow']])}</section>
<section><h2>ต่างชาติซื้อสุทธิในตลาดหุ้น (ล้านบาท/วัน)</h2>{_svg_bars(f['foreign_net']) if 'foreign_net' in f else ''}</section>
{tfex_block}
<section><h2>คะแนนรวม</h2>{_svg_line([score.tail(lookback)], zero_line=True)}</section>
{breadth_block}
{"<section><h2>ทดสอบย้อนหลัง (ทั้งช่วง · พารามิเตอร์เริ่มต้น)</h2><div class=grid>" + kpi + "</div></section>" if kpi else ""}
{eq}
{hyp}
<p class=note>สร้างโดย tfexflow · ไม่ใช่คำแนะนำการลงทุน · ทุกการตัดสินใจเป็นของผู้ใช้</p>
</body></html>"""
