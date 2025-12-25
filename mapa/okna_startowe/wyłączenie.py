import time
from pathlib import Path

time.sleep(1)

dir_path = Path(__file__).parent
src = dir_path / "start.py"
dst = dir_path / "off.py"

if src.exists():
    src.rename(dst)
