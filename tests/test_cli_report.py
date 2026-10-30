import json

from tfexflow.cli import main


def test_signal_และ_report_สร้างไฟล์ครบ(sample_dir, tmp_path):
    out = tmp_path / "out"
    assert main(["signal", "--data", str(sample_dir), "--out", str(out)]) == 0
    sig = json.loads((out / "signal.json").read_text(encoding="utf-8"))
    assert sig["state"] in {"LONG", "SHORT", "FLAT"} and sig["synthetic"] is True
    assert -1 <= sig["score"] <= 1 and sig["suggested_contracts"] >= 0
    assert main(["report", "--data", str(sample_dir), "--out", str(out)]) == 0
    html = (out / "report.html").read_text(encoding="utf-8")
    assert sig["state"] in html and "ข้อมูลจำลอง" in html and "<script" not in html


def test_hypothesis_และ_backtest_รันผ่าน(sample_dir, tmp_path):
    out = tmp_path / "out2"
    assert main(["hypothesis", "--data", str(sample_dir), "--out", str(out)]) == 0
    assert main(["backtest", "--data", str(sample_dir), "--out", str(out), "--no-wf"]) == 0
    assert (out / "hypothesis_verdict.csv").exists() and (out / "backtest_trades.csv").exists()
