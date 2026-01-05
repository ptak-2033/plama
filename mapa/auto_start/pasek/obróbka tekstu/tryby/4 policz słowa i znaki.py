from pathlib import Path
ROOT = Path(__file__).resolve().parent
TEKST = ROOT / "tekst.txt"

data = TEKST.read_text(encoding="utf-8", errors="ignore")

words = len(data.split())
chars = len(data)

info = f"\n[Słowa: {words}, Znaki: {chars}]\n"

processed = data + info

TEKST.write_text(processed, encoding="utf-8")
