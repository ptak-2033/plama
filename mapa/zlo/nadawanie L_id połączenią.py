from pathlib import Path

def main():
    # 🧭 Standard opcji „zlo”
    try:
        current_file = Path(__file__).resolve()
    except NameError:
        current_file = Path.cwd().resolve()

    try:
        parent2 = current_file.parents[2]
    except Exception:
        parent2 = current_file.parent

    linie_dir = parent2 / "linie"
    obiekty_dir = parent2 / "obiekty"  # trzymamy w standardzie, choć tu nie używamy

    if not linie_dir.exists() or not linie_dir.is_dir():
        return  # brak katalogu linii → nic nie robimy

    # 🔎 zbieramy podfoldery = linie
    linia_folders = [p for p in linie_dir.iterdir() if p.is_dir()]
    if not linia_folders:
        return

    folders_with_lid = []
    folders_without_lid = []
    used_ids = set()

    # 1) Czytamy istniejące L_id.txt
    for lf in linia_folders:
        lid_file = lf / "L_id.txt"
        if lid_file.exists():
            try:
                raw = lid_file.read_text(encoding="utf-8").strip()
                if raw != "":
                    val = int(raw)
                    used_ids.add(val)
                    folders_with_lid.append((lf, val))
                else:
                    # pusty plik traktujemy jak brak ID
                    folders_without_lid.append(lf)
            except Exception:
                # śmieci w pliku → traktujemy jak brak ID
                folders_without_lid.append(lf)
        else:
            folders_without_lid.append(lf)

    # jeśli każda linia ma poprawne L_id → nic nie robimy
    if len(folders_without_lid) == 0:
        return

    # 2) ustalamy punkt startowy dla nowych ID
    max_used = max(used_ids) if used_ids else 0
    next_id = max_used + 1

    # 3) nadajemy unikalne ID wszystkim bez L_id
    for lf in folders_without_lid:
        lid_file = lf / "L_id.txt"
        try:
            lid_file.write_text(str(next_id), encoding="utf-8")
            next_id += 1
        except Exception:
            # jak się wywali na pojedynczym folderze, lecimy dalej
            continue


if __name__ == "__main__":
    main()
