#!/usr/bin/env python3
from pathlib import Path
import re
import sys

# sync_linie_no_backup.py
# Bez backupów, bez duplikowania linii. Uruchamiany z poziomu pliku (używa __file__).

def parse_kv_file(path: Path):
    data = {}
    lines = path.read_text(encoding='utf-8').splitlines()
    for ln in lines:
        m = re.match(r'\s*([^=#\s]+)\s*=\s*(.+)\s*$', ln)
        if m:
            data[m.group(1)] = m.group(2)
    return data, lines

def find_two_ints(text):
    m = re.search(r'(-?\d+)\s+(-?\d+)', text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None

def set_xy_in_lines_replace_once(lines, key, x, y):
    """Usuń wszystkie linie pasujące do klucza i dopisz jedną linię key=x y."""
    pat = re.compile(r'^\s*' + re.escape(key) + r'\s*=\s*.*$', re.IGNORECASE)
    # keep only lines that are NOT the key
    new_lines = [ln for ln in lines if not pat.match(ln)]
    new_lines.append(f"{key}={x} {y}")
    return new_lines

def main():
    try:
        current_file = Path(__file__).resolve()
    except NameError:
        current_file = Path.cwd().resolve()

    try:
        parent2 = current_file.parents[2]
    except Exception:
        parent2 = current_file.parent

    linie_dir = parent2 / "linie"
    obiekty_dir = parent2 / "obiekty"

    if not linie_dir.exists() or not obiekty_dir.exists():
        print("Brakuje folderu 'linie' lub 'obiekty' w parent2. Sprawdź strukturę.")
        return 1

    pairs = []
    for ab in linie_dir.rglob('AB.txt'):
        ld = ab.parent / "linia_dane.txt"
        if ld.exists():
            pairs.append((ab, ld))

    if not pairs:
        print("Brak plików AB.txt + linia_dane.txt w 'linie'.")
        return 0

    # index objects
    id_index = {}
    for obj_folder in obiekty_dir.rglob('*'):
        if not obj_folder.is_dir():
            continue
        idf = obj_folder / "id.txt"
        md = obj_folder / "mapa_dane.txt"
        if idf.exists() and md.exists():
            id_val = idf.read_text(encoding='utf-8').strip()
            mapa_txt = md.read_text(encoding='utf-8')
            mx = re.search(r'\bX\s*=\s*(-?\d+)', mapa_txt)
            my = re.search(r'\bY\s*=\s*(-?\d+)', mapa_txt)
            xy = None
            if mx and my:
                xy = (int(mx.group(1)), int(my.group(1)))
            else:
                mxy = re.search(r'\bxy\s*=\s*(-?\d+)\s+(-?\d+)', mapa_txt, re.IGNORECASE)
                if mxy:
                    xy = (int(mxy.group(1)), int(mxy.group(2)))
                else:
                    p = re.search(r'(-?\d+)\s+(-?\d+)', mapa_txt)
                    if p:
                        xy = (int(p.group(1)), int(p.group(2)))
            id_index[id_val] = {"folder": obj_folder, "xy": xy, "mapa_path": md}

    for ab_path, ld_path in pairs:
        ab_kv, _ = parse_kv_file(ab_path)
        _, ld_lines = parse_kv_file(ld_path)

        xy1 = None
        xy2 = None
        for ln in ld_lines:
            if ln.strip().lower().startswith('xy1='):
                xy1 = find_two_ints(ln)
            if ln.strip().lower().startswith('xy2='):
                xy2 = find_two_ints(ln)

        a_id = ab_kv.get('obiekt_A')
        b_id = ab_kv.get('obiekt_B')
        modified = False

        # process A
        if a_id and a_id in id_index:
            obj_xy = id_index[a_id]["xy"]
            if obj_xy is not None:
                if xy1 is None or (xy1[0], xy1[1]) != (obj_xy[0], obj_xy[1]):
                    ld_lines = set_xy_in_lines_replace_once(ld_lines, 'xy1', obj_xy[0], obj_xy[1])
                    modified = True

        # process B
        if b_id and b_id in id_index:
            obj_xy = id_index[b_id]["xy"]
            if obj_xy is not None:
                if xy2 is None or (xy2[0], xy2[1]) != (obj_xy[0], obj_xy[1]):
                    ld_lines = set_xy_in_lines_replace_once(ld_lines, 'xy2', obj_xy[0], obj_xy[1])
                    modified = True

        if modified:
            # zapis bez backupu, bez duplikatów
            ld_path.write_text("\n".join(ld_lines) + "\n", encoding='utf-8')
            print(f"Zapisano {ld_path} (bez backupu).")
        else:
            print(f"Brak zmian w {ld_path}.")

    print("Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
