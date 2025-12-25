from pathlib import Path
import shutil
import sys

current_file = Path(__file__).resolve()
target = current_file.parents[2] / "obiekty"
kosz = current_file.parents[2] / "kosz"

kosz.mkdir(parents=True, exist_ok=True)

def move_with_copies(src: Path, dest_dir: Path):
    """
    Przenosi (WYCIĄGA) folder z src do dest_dir.
    Jeśli w koszu istnieje folder o tej nazwie – robi ' - kopia', ' - kopia 2', itd.
    Oryginał z obiektów znika (to nie jest kopiowanie!).
    """
    base_name = src.name
    target = dest_dir / base_name

    if target.exists():
        counter = 1
        while True:
            suffix = " - kopia" if counter == 1 else f" - kopia {counter}"
            new_target = dest_dir / f"{base_name}{suffix}"
            if not new_target.exists():
                target = new_target
                break
            counter += 1

    shutil.move(str(src), str(target))
    print(f"Wycięto -> {target}")

def main() -> int:
    if not target.exists() or not target.is_dir():
        print("Nie znaleziono folderu 'obiekty' dwa poziomy wyżej.")
        return 1

    moved_any = False
    for folder in target.iterdir():
        if not folder.is_dir():
            continue
        mapa_file = folder / "mapa_dane.txt"
        if not mapa_file.exists():
            print(f"{folder.name} -> brak mapa_dane.txt, przenoszę do kosza")
            try:
                move_with_copies(folder, kosz)
                moved_any = True
            except Exception as e:
                print(f"Błąd przy przenoszeniu {folder.name}: {e}")

    if not moved_any:
        print("Brak nieznanych obiektów do przeniesienia.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
