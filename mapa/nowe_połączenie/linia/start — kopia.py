#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PLAMA GEN5 — LINIA ŚWIADOMA 🧠

Zasada:
- DATA: wyjście A + wejście B → kopiuj → weryfikuj → start B
- TRIGGER: brak wyjścia A + brak wejścia B → log → start B
- NIESPÓJNOŚĆ: jeden jest, drugiego brak → STOP
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


# =============== LOGI ===============
def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        with open(PATH_LOG, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass
    print(line, end="")


# =============== UTILS ===============
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


# =============== LOGIKA LINII ===============
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


def copy_verify_and_maybe_start(obj_a: Path, obj_b: Path):
    path_out = obj_a / "wyjście.txt"
    path_in = obj_b / "wejście.txt"

    has_out = path_out.exists()
    has_in = path_in.exists()

    # === TRYB DATA ===
    if has_out and has_in:
        data_a = read_text(path_out)
        atomic_write(path_in, data_a)
        data_b = read_text(path_in)

        if data_a == data_b:
            log("[LINIA] Dane zgodne A→B")
            run_object_start(obj_b)
        else:
            log("[LINIA ERROR] Dane NIEZGODNE po kopiowaniu — STOP")
        return

    # === TRYB TRIGGER ===
    if not has_out and not has_in:
        log("[LINIA] Brak wyjście.txt u A")
        log("[LINIA] Brak wejście.txt u B")
        log("[LINIA] Tryb TRIGGER")
        run_object_start(obj_b)
        return

    # === NIESPÓJNOŚĆ ===
    if has_out and not has_in:
        log("[LINIA ERROR] A ma wyjście, B nie ma wejścia — STOP")
    elif not has_out and has_in:
        log("[LINIA ERROR] B ma wejście, A nie ma wyjścia — STOP")


# =============== MAIN ===============
def main():
    log("=== START LINII ===")
    set_proces("on")
    try:
        id_a, id_b = parse_AB(PATH_AB)
        obj_a = find_object_dir_by_id(Path(__file__).resolve(), id_a)
        obj_b = find_object_dir_by_id(Path(__file__).resolve(), id_b)

        copy_verify_and_maybe_start(obj_a, obj_b)

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
