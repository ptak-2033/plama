import random
import shutil
from pathlib import Path

def find_dir(name, start: Path):
    for p in [start] + list(start.parents):
        candidate = p / name
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"Nie znaleziono folderu {name}")

SCRIPT_DIR = Path(__file__).resolve()
LINIE_DIR = find_dir("linie", SCRIPT_DIR)
SIEC_TEMPLATE_DIR = SCRIPT_DIR.parent / "sieć"
OBIEKTY_DIR = LINIE_DIR.parent / "obiekty"

# === INDEKS OBIEKTÓW (id -> folder) ===
object_index = {}

for obj in OBIEKTY_DIR.iterdir():
    if not obj.is_dir():
        continue

    id_file = obj / "id.txt"
    if id_file.exists():
        obj_id = id_file.read_text(encoding="utf-8").strip()
        object_index[obj_id] = obj

def read_a_value(linia_dir):
    ab = linia_dir / "ab.txt"
    if not ab.exists():
        return None
    for line in ab.read_text(encoding="utf-8").splitlines():
        if line.startswith("obiekt_A="):
            return line.split("=", 1)[1].strip()
    return None

# a_value -> [(kontener, linia_dir)]
groups = {}

for kontener in LINIE_DIR.iterdir():
    if not kontener.is_dir():
        continue
    for linia in kontener.iterdir():
        if not linia.is_dir():
            continue
        a_val = read_a_value(linia)
        if a_val is None:
            continue
        groups.setdefault(a_val, []).append((kontener, linia))

for a_val, entries in groups.items():
    by_container = {}
    for kontener, linia in entries:
        by_container.setdefault(kontener, []).append(linia)

    stable = {k: v for k, v in by_container.items() if len(v) > 1}
    singles = {k: v[0] for k, v in by_container.items() if len(v) == 1}

    # jeśli jest stabilna grupa – dokładamy samotne
    if stable:
        target_container = next(iter(stable))
        for src_container, linia in singles.items():
            new_index = len(list(target_container.iterdir())) + 1
            new_name = f"linia{new_index}"
            shutil.move(str(linia), target_container / new_name)

    else:
        # === ZMIENIONY PUNKT 4 ===
        if len(singles) == 2:
            (c1, l1), (c2, l2) = random.sample(list(singles.items()), 2)

            target_container = c1
            source_linia = l2

            # znajdź wolną nazwę siećN
            parent = target_container.parent
            n = 1
            while (parent / f"sieć{n}").exists():
                n += 1
            siec_dir = parent / f"sieć{n}"

            # zmień nazwę kontenera na siećN
            target_container.rename(siec_dir)

            # skopiuj szablon sieci
            if SIEC_TEMPLATE_DIR.exists():
                for item in SIEC_TEMPLATE_DIR.iterdir():
                    dest = siec_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)

            # przenieś linię do siećN
            new_index = len([p for p in siec_dir.iterdir() if p.is_dir() and p.name.startswith("linia")]) + 1
            shutil.move(str(source_linia), siec_dir / f"linia{new_index}")

# === GLOBAL CLEANUP ===
# kontener bez podfolderu linia* = śmieć
for kontener in LINIE_DIR.iterdir():
    if not kontener.is_dir():
        continue
    if not any(p.is_dir() and p.name.startswith("linia") for p in kontener.iterdir()):
        shutil.rmtree(kontener)

def get_object_ids_from_siec(kontener: Path):
    ids = set()

    for linia in kontener.iterdir():
        if not linia.is_dir() or not linia.name.startswith("linia"):
            continue

        ab = linia / "ab.txt"
        if not ab.exists():
            continue

        for line in ab.read_text(encoding="utf-8").splitlines():
            if line.startswith("obiekt_A=") or line.startswith("obiekt_B="):
                ids.add(line.split("=", 1)[1].strip())

    return ids

# === BUDOWANIE lista.txt (A = anchor, B = opcjonalne) ===

def write_lista_txt(kontener: Path, anchor_id: str, object_index: dict):
    lines = []
    allowed_ids = get_object_ids_from_siec(kontener)

    # === A (anchor) ===
    if anchor_id and anchor_id in object_index:
        anchor_name = object_index[anchor_id].name
        lines.append(f"A; id={anchor_id}; name={anchor_name}")

    # === B (DANE W LISTA.TXT, NIE W PLIKACH) ===
    for obj_id, obj_dir in object_index.items():
        if obj_id not in allowed_ids:
            continue
        if obj_id == anchor_id:
            continue

        name = obj_dir.name

        # 🔧 TU USTAWIASZ LOGIKĘ DOMYŚLNĄ
        # (na razie na sztywno, później możesz to zmienić)
        sygnal = "1"
        impuls = "on"

        parts = ["B"]

        # id opcjonalne
        parts.append(f"id={obj_id}")

        # name obowiązkowe
        parts.append(f"name={name}")

        # sygnal + impuls ZAWSZE
        parts.append(f"sygnal={sygnal}")
        parts.append(f"impuls={impuls}")

        lines.append("; ".join(parts))

    (kontener / "lista.txt").write_text(
        "\n".join(lines) if lines else "# lista pusta",
        encoding="utf-8"
    )

# === WYWOŁANIE DLA KAŻDEJ SIECI ===

for kontener in LINIE_DIR.iterdir():
    if not kontener.is_dir():
        continue
    if not kontener.name.startswith("sieć"):
        continue

    anchor_id = None  # <-- TO MUSI BYĆ

for linia in kontener.iterdir():
    if not linia.is_dir() or not linia.name.startswith("linia"):
        continue

    ab = linia / "ab.txt"
    if not ab.exists():
        continue

    for line in ab.read_text(encoding="utf-8").splitlines():
        if line.startswith("obiekt_A="):
            anchor_id = line.split("=", 1)[1].strip()
            break

    if anchor_id:
        break

write_lista_txt(kontener, anchor_id, object_index)


