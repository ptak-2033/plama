from pathlib import Path
ROOT = Path(__file__).resolve().parent
TEKST = ROOT / "tekst.txt"

data = TEKST.read_text(encoding="utf-8", errors="ignore")

processed = "\n".join(
    line for line in data.splitlines()
    if line.strip() != ""
)

TEKST.write_text(processed, encoding="utf-8")
