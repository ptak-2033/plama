from pathlib import Path

# katalog, w którym jest proces.py
BASE_DIR = Path(__file__).resolve().parent

wejscie_path = BASE_DIR / "wejście.txt"
tekst_path = BASE_DIR / "tekst.txt"
sygnal_path = BASE_DIR / "sygnał.txt"

# zabezpieczenie jakby czegoś brakowało
if not wejscie_path.exists() or not tekst_path.exists():
    sygnal_path.write_text("0", encoding="utf-8")
    exit(0)

# czytamy wejście jako jeden ciąg
wejscie_text = wejscie_path.read_text(encoding="utf-8")

# flag
found = False

# sprawdzamy linia po linii
for line in tekst_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue  # pomijamy puste linie

    # szukamy CAŁEJ LINII jako ciąg słów obok siebie
    if line in wejscie_text:
        found = True
        break

# zapis sygnału
sygnal_path.write_text("1" if found else "0", encoding="utf-8")
