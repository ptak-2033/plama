from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEKST = ROOT / "tekst.txt"

data = TEKST.read_text(encoding="utf-8", errors="ignore")

# --- operacja ---
processed = data  # <- tutaj tryb robi swoje

TEKST.write_text(processed, encoding="utf-8")

from pathlib import Path
ROOT = Path(__file__).resolve().parent
TEKST = ROOT / "tekst.txt"

data = TEKST.read_text(encoding="utf-8", errors="ignore")
processed = data[::-1]

TEKST.write_text(processed, encoding="utf-8")
