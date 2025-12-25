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
    obiekty_by_id = {}
    if not obiekty_dir.is_dir():
        return obiekty_by_id

    for obj_folder in obiekty_dir.iterdir():
        if not obj_folder.is_dir():
            continue

        id_file = obj_folder / "id.txt"
        if not id_file.is_file():
            continue

        try:
            obj_id = id_file.read_text(encoding="utf-8").strip()
        except Exception:
            continue

        if obj_id:
            obiekty_by_id[obj_id] = obj_folder

    return obiekty_by_id


def get_obiekt_A_from_ab(ab_file: Path):
    try:
        content = ab_file.read_text(encoding="utf-8")
    except Exception:
        return None

    obiekt_A = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("obiekt_A="):
            obiekt_A = line.split("=", 1)[1].strip()
            break
    return obiekt_A


def main():
    linie_dir, obiekty_dir = resolve_base_dirs()

    if not linie_dir.is_dir() or not obiekty_dir.is_dir():
        print("Brak folderu 'linie/' albo 'obiekty/' – nic nie robię.")
        return

    obiekty_by_id = load_obiekty_by_id(obiekty_dir)

    for linia_folder in linie_dir.iterdir():
        if not linia_folder.is_dir():
            continue

        ab_file = linia_folder / "AB.txt"
        if not ab_file.is_file():
            continue

        obiekt_A = get_obiekt_A_from_ab(ab_file)
        if not obiekt_A:
            continue

        # jeśli chcesz TYLKO obiekt_A=1, odkomentuj to:
        # if obiekt_A != "1":
        #     continue

        l_id_file = linia_folder / "L_id.txt"
        if not l_id_file.is_file():
            # brak L_id.txt – pomijamy
            continue

        try:
            l_content = l_id_file.read_text(encoding="utf-8")
        except Exception:
            continue

        obj_folder = obiekty_by_id.get(obiekt_A)
        if not obj_folder:
            # nie znaleziono obiektu z tym id
            continue

        nastepny_file = obj_folder / "następny.txt"
        try:
            nastepny_file.write_text(l_content, encoding="utf-8")
            print(f"[OK] {nastepny_file} ← L_id z linii {linia_folder.name} (obiekt_A={obiekt_A})")
        except Exception as e:
            print(f"[ERR] Nie mogę zapisać {nastepny_file}: {e}")


if __name__ == "__main__":
    main()
