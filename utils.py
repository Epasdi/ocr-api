import os
from pathlib import Path

QUAR_DIR = Path(os.getenv("QUAR_DIR", "/srv/quarantine"))
QUAR_DIR.mkdir(parents=True, exist_ok=True)

def clamp(n, a, b): return max(a, min(n, b))
