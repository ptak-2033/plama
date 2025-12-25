# plik: mapa/nowe_połączenie/dodawanie.py
from pathlib import Path
import re, sys, io, shutil

RX_XY = re.compile(r"^xy\s*=\s*(-?\d+)\s+(-?\d+)\s*$", re.M)

def find_root(script_dir: Path) -> Path:
    for anc in [script_dir] + list(script_dir.parents):
        if (anc / "mapa").is_dir() and (anc / "obiekty").is_dir() and (anc / "linie").is_dir():
            return anc
    print("❌ Nie znalazłem folderu z 'mapa', 'obiekty', 'linie'.")
    sys.exit(1)

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def parse_ab(ab_path: Path):
    if not ab_path.exists():
        print(f"❌ Brak pliku: {ab_path}")
        sys.exit(1)
    A = B = None
    for line in read_text(ab_path).splitlines():
        s = line.strip()
        if s.startswith("obiekt_A="):
            A = s.split("=",1)[1].strip()
        elif s.startswith("obiekt_B="):
            B = s.split("=",1)[1].strip()
    if not A or not B:
        print("❌ AB.txt musi mieć 'obiekt_A=' i 'obiekt_B='.")
        sys.exit(1)
    return A, B

def find_object_dir_by_id(obiekty_dir: Path, wanted_id: str):
    for obj_dir in obiekty_dir.iterdir():
        if not obj_dir.is_dir():
            continue
        id_file = obj_dir / "id.txt"
        if id_file.exists() and read_text(id_file).strip() == wanted_id:
            return obj_dir
    return None

def read_xy(mapa_dane_path: Path):
    if not mapa_dane_path.exists():
        return None
    m = RX_XY.search(read_text(mapa_dane_path))
    return (int(m.group(1)), int(m.group(2))) if m else None

def set_key_lines(content: str, key: str, val: str) -> str:
    rx = re.compile(rf"^{re.escape(key)}\s*=\s*.*$", re.M)
    line = f"{key}={val}"
    if rx.search(content):
        return rx.sub(line, content, count=1)
    if content and not content.endswith("\n"):
        content += "\n"
    return content + line + "\n"

def next_free_line_folder(linie_dir: Path) -> Path:
    linie_dir.mkdir(exist_ok=True)
    n = 1
    while True:
        candidate = linie_dir / f"linia {n}"
        if not candidate.exists():
            return candidate
        n += 1

def copy_template_new_line(template_dir: Path, linie_dir: Path) -> Path:
    """Zawsze tworzy NOWY folder 'linia N' z kopią szablonu."""
    if not template_dir.is_dir():
        print(f"❌ Brak folderu szablonu linii: {template_dir}")
        sys.exit(1)
    target = next_free_line_folder(linie_dir)
    shutil.copytree(template_dir, target)  # nowy katalog, więc copytree przejdzie
    return target

def copy_or_overwrite_ab(target: Path, ab_path: Path):
    """Wstawia AB.txt do nowo utworzonej linii (nadpisze jeśli cokolwiek tam już było)."""
    shutil.copy2(ab_path, target / "AB.txt")

def write_xy_to_linia_dane(linia_folder: Path, xy1, xy2):
    linia_dane_path = linia_folder / "linia_dane.txt"
    content = read_text(linia_dane_path) if linia_dane_path.exists() else ""
    content = set_key_lines(content, "xy1", f"{xy1[0]} {xy1[1]}")
    content = set_key_lines(content, "xy2", f"{xy2[0]} {xy2[1]}")
    with io.open(linia_dane_path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(content)

def main():
    script_dir = Path(__file__).parent.resolve()   # .../mapa/nowe_połączenie
    ab_path    = script_dir / "AB.txt"             # obok skryptu
    template   = script_dir / "linia"              # SZABLON (obok skryptu)

    A, B = parse_ab(ab_path)

    root      = find_root(script_dir)              # rodzic z mapa/obiekty/linie
    obiekty   = root / "obiekty"
    linie_dir = root / "linie"

    objA = find_object_dir_by_id(obiekty, A)
    objB = find_object_dir_by_id(obiekty, B)
    if not objA:
        print(f"❌ Nie znalazłem obiektu o id={A} w {obiekty}")
        sys.exit(1)
    if not objB:
        print(f"❌ Nie znalazłem obiektu o id={B} w {obiekty}")
        sys.exit(1)

    xyA = read_xy(objA / "mapa_dane.txt")
    xyB = read_xy(objB / "mapa_dane.txt")
    if xyA is None:
        print(f"❌ Brak 'xy=' w {objA / 'mapa_dane.txt'}")
        sys.exit(1)
    if xyB is None:
        print(f"❌ Brak 'xy=' w {objB / 'mapa_dane.txt'}")
        sys.exit(1)

    # ZAWSZE: nowa linia N skopiowana z szablonu
    new_line_folder = copy_template_new_line(template, linie_dir)

    # Dorzuć/ nadpisz AB.txt w tej nowej linii
    copy_or_overwrite_ab(new_line_folder, ab_path)

    # Zapisz XY
    write_xy_to_linia_dane(new_line_folder, xyA, xyB)

    print(f"✅ Utworzono: {new_line_folder.name}")
    print(f"   AB.txt → {new_line_folder / 'AB.txt'} (nadpisane jeśli istniało)")
    print(f"   xy1={xyA[0]} {xyA[1]}, xy2={xyB[0]} {xyB[1]} zapisane w {new_line_folder / 'linia_dane.txt'}")

if __name__ == "__main__":
    main()
