from pathlib import Path

# plik tego skryptu
current_file = Path(__file__).resolve()

# dwa poziomy wyżej
target = current_file.parents[2] / "mapa_dane.txt"

if target.exists():
    target.unlink()
    print(f"🗑️ Usunięto: {target}")
else:
    print(f"⚠️ Nie znaleziono: {target}")
