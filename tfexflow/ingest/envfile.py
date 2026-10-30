"""อ่านไฟล์ .env แบบง่าย — ไม่เพิ่ม dependency (python-dotenv) เพื่อของไม่กี่บรรทัด

★ ค่าที่อ่านได้ไม่ถูกพิมพ์ออกจอหรือเขียนลง log ที่ไหนเลย · ไฟล์ .env ถูก ignore ใน git แล้ว
"""
import os
from pathlib import Path


def load_env(path: str | Path = ".env", override: bool = False) -> list[str]:
    """ใส่ค่าลง os.environ · คืนรายชื่อคีย์ที่โหลด (ไม่คืนค่า)"""
    p = Path(path)
    if not p.exists():
        return []
    keys = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip().removeprefix("export ").strip()
        v = v.strip().strip('"').strip("'")
        if override or k not in os.environ:
            os.environ[k] = v
        keys.append(k)
    return keys
