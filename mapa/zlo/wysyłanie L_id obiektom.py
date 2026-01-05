from pathlib import Path


def resolve_base_dirs():
    # standard opcji "zlo"
    try:
        current_file = Path(__file__).resolve()
    except NameError:
        current_file = Path.cwd().resolve()

    try:
        parent2 = current_file.parents[2]
    except IndexError:
        parent2 = current_file.parent

    linie_dir = parent2 / "linie"
    obiekty_dir = parent2 / "obiekty"
    return linie_dir, obiekty_dir


def load_obiekty_by_id(obiekty_dir: Path):
    obiekty = {}
    if not obiekty_dir.is_dir():
        return obiekty

    for obj in obiekty_dir.iterdir():
        if not obj.is_dir():
            continue

        id_file = obj / "id.txt"
        if not id_file.is_file():
            continue

        try:
            obj_id = id_file.read_text(encoding="utf-8").strip()
        except Exception:
            continue

        if obj_id:
            obiekty[obj_id] = obj

    return obiekty


def read_obiekt_A(ab_file: Path):
    try:
        content = ab_file.read_text(encoding="utf-8")
    except Exception:
        return None

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("obiekt_A="):
            return line.split("=", 1)[1].strip()

    return None


def main():
    linie_dir, obiekty_dir = resolve_base_dirs()

    if not linie_dir.is_dir() or not obiekty_dir.is_dir():
        print("[STOP] Brak folderu 'linie/' lub 'obiekty/'")
        return

    obiekty_by_id = load_obiekty_by_id(obiekty_dir)

    # === SKANUJEMY KONTENERY ===
    for kontener in linie_dir.iterdir():
        if not kontener.is_dir():
            continue

        l_id_file = kontener / "L_id.txt"
        if not l_id_file.is_file():
            continue  # kontener bez L_id = martwy

        znalezione_A = set()

        # sprawdzamy WSZYSTKIE linie w kontenerze
        for linia in kontener.iterdir():
            if not linia.is_dir():
                continue

            ab_file = linia / "AB.txt"
            if not ab_file.is_file():
                continue

            a_val = read_obiekt_A(ab_file)
            if a_val:
                znalezione_A.add(a_val)

        if not znalezione_A:
            print(f"[SKIP] {kontener.name} – brak obiekt_A w liniach")
            continue

        if len(znalezione_A) > 1:
            print(f"[ERR] {kontener.name} – różne obiekt_A: {znalezione_A}")
            continue

        obiekt_A = next(iter(znalezione_A))
        obj_folder = obiekty_by_id.get(obiekt_A)

        if not obj_folder:
            print(f"[MISS] Brak obiektu id={obiekt_A} dla {kontener.name}")
            continue

        try:
            l_content = l_id_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[ERR] Nie mogę czytać {l_id_file}: {e}")
            continue

        nastepny = obj_folder / "następny.txt"
        try:
            nastepny.write_text(l_content, encoding="utf-8")
            print(f"[OK] {obj_folder.name}/następny.txt ← {kontener.name}/L_id.txt")
        except Exception as e:
            print(f"[ERR] Zapis do {nastepny} nieudany: {e}")


if __name__ == "__main__":
    main()
