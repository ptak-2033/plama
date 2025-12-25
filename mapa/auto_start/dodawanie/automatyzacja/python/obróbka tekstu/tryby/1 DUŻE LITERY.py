from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEKST = ROOT / "tekst.txt"

data = TEKST.read_text(encoding="utf-8", errors="ignore")

# --- operacja ---
processed = data  # <- tutaj tryb robi swoje

TEKST.write_text(processed, encoding="utf-8")

ROOT = Path(__file__).resolve().parent
TEKST = ROOT / "tekst.txt"

data = TEKST.read_text(encoding="utf-8", errors="ignore")
processed = data.upper()

TEKST.write_text(processed, encoding="utf-8")