#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PLAMA GEN5 — LINIA STANOWA (all.txt w B)
"""

import os
import sys
import time
import datetime
import tempfile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATH_AB = ROOT / "AB.txt"
PATH_LINIA_DANE = ROOT / "linia_dane.txt"
PATH_LOG = ROOT / "linia_log.txt"


# ===== LOG =====
def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        with open(PATH_LOG, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass
    print(line, end="")


# ===== UTILS =====
def read_text(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""


def atomic_write(path: Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=str(path.parent))
    with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
        f.write(data)
    os.replace(tmp, str(path))


def set_proces(status: str):
    lines = read_text(PATH_LINIA_DANE).splitlines() if PATH_LINIA_DANE.exists() else []
    out, hit = [], False
    for line in lines:
        if line.strip().lower().startswith("proces="):
            out.append(f"proces={status}")
            hit = True
        else:
            out.append(line)
    if not hit:
        out.append(f"proces={status}")
    atomic_write(PATH_LINIA_DANE, "\n".join(out) + "\n")
    log(f"[LINIA] proces={status}")


# ===== LOGIKA =====
def parse_AB(path: Path):
    txt = read_text(path)
    id_a = id_b = None
    for raw in txt.splitlines():
        if "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        if k.strip().lower() == "obiekt_a":
            id_a = v.strip()
        elif k.strip().lower() == "obiekt_b":
            id_b = v.strip()
    if not id_a or not id_b:
        raise RuntimeError("AB.txt niepoprawny")
    return id_a, id_b


def find_object_dir_by_id(script_path: Path, target_id: str) -> Path:
    try:
        root = script_path.parents[2]
    except IndexError:
        root = script_path.parent
    obiekty = root / "obiekty"
    for obj in obiekty.iterdir():
        if obj.is_dir() and (obj / "id.txt").exists():
            if read_text(obj / "id.txt") == target_id:
                return obj
    raise RuntimeError(f"Brak obiektu id={target_id}")


def run_object_start(obj_b: Path):
    start_script = obj_b / "start.py"
    if not start_script.exists():
        log("[LINIA] Brak start.py u B → ignoruję")
        return
    subprocess.Popen(
        [sys.executable, str(start_script)],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    log("[LINIA] Odpalono obiekt B")


def copy_and_route(obj_a: Path, obj_b: Path):
    path_out_a = obj_a / "wyjście.txt"

    if not path_out_a.exists():
        log("[LINIA ERROR] Brak wyjście.txt u A — STOP")
        return

    data = read_text(path_out_a)

    # ===== TRYB STANOWY (all.txt tylko w B) =====
    path_all_b = obj_b / "all.txt"
    if path_all_b.exists():
        atomic_write(path_all_b, data)
        atomic_write(obj_b / "wejście.txt", data)
        atomic_write(obj_b / "wyjście.txt", data)
        log("[LINIA] all.txt w B — przeniesiono STAN A→B")
        run_object_start(obj_b)
        return

    # ===== TRYB KLASYCZNY =====
    path_in_b = obj_b / "wejście.txt"
    if not path_in_b.exists():
        log("[LINIA ERROR] B nie ma wejście.txt — STOP")
        return

    atomic_write(path_in_b, data)
    if read_text(path_in_b) == data:
        log("[LINIA] Dane zgodne A→B")
        run_object_start(obj_b)
    else:
        log("[LINIA ERROR] Dane niezgodne po kopiowaniu — STOP")


# ===== MAIN =====
def main():
    log("=== START LINII ===")
    set_proces("on")
    try:
        id_a, id_b = parse_AB(PATH_AB)
        obj_a = find_object_dir_by_id(Path(__file__).resolve(), id_a)
        obj_b = find_object_dir_by_id(Path(__file__).resolve(), id_b)

        copy_and_route(obj_a, obj_b)

        time.sleep(1)
        set_proces("off")
        log("=== KONIEC LINII OK ===")
        return 0

    except Exception as e:
        log(f"[LINIA ERROR] {e}")
        set_proces("error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
