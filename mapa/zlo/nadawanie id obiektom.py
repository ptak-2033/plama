#!/usr/bin/env python3
from pathlib import Path
import sys

def main() -> int:
    current_file = Path(__file__).resolve()
    target = current_file.parents[2] / "obiekty"

    if not target.exists() or not target.is_dir():
        print(f"💀 Nie znaleziono folderu: {target}")
        return 1

    used_ids = set()
    for sub in target.iterdir():
        if not sub.is_dir():
            continue
        id_file = sub / "id.txt"
        if id_file.exists():
            try:
                used_ids.add(int(id_file.read_text(encoding="utf-8").strip()))
            except ValueError:
                print(f"⚠️  Nieprawidłowy format w {id_file}, pomijam.")

    def next_free_id(used):
        i = 1
        while i in used:
            i += 1
        return i

    new_count = 0
    for sub in sorted([p for p in target.iterdir() if p.is_dir()]):
        id_file = sub / "id.txt"
        if id_file.exists():
            continue
        new_id = next_free_id(used_ids)
        id_file.write_text(str(new_id) + "\n", encoding="utf-8")
        used_ids.add(new_id)
        new_count += 1
        print(f"✅ Nadano ID {new_id} → {sub.name}")

    if new_count == 0:
        print("👌 Wszystkie obiekty mają ID.")
    else:
        print(f"🔥 Nadano {new_count} brakujących ID.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
