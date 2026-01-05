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
    """
    Idzie w górę od miejsca uruchomienia,
    aż znajdzie folder 'obiekty/',
    a potem szuka w nim obiektu po id.txt
    """
    # 🔍 szukamy rootu, który zawiera 'obiekty/'
    root = None
    for p in [script_path] + list(script_path.parents):
        if (p / "obiekty").is_dir():
            root = p
            break

    if root is None:
        raise RuntimeError("Nie znaleziono folderu 'obiekty/' w górę drzewa")

    obiekty_dir = root / "obiekty"

    # 🔎 szukamy konkretnego obiektu po id.txt
    for obj in obiekty_dir.iterdir():
        if not obj.is_dir():
            continue

        id_file = obj / "id.txt"
        if not id_file.is_file():
            continue

        try:
            if id_file.read_text(encoding="utf-8", errors="replace").strip() == target_id:
                return obj
        except Exception:
            continue

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
    # =========================================================
    # TRYB LUSTRA / STANOWY
    # all.txt = bypass żył
    # wyjście A -> wejście B + wyjście B (1:1)
    # =========================================================
    if (obj_b / "all.txt").exists():
        data = read_text(obj_a / "wyjście.txt")

        atomic_write(obj_b / "wejście.txt", data)
        atomic_write(obj_b / "wyjście.txt", data)

        log("[LINIA] TRYB all → mirror stanu A → B (wejście=wyjście)")
        run_object_start(obj_b)
        return

    # =========================================================
    # ŻYŁA 1 — DANE
    # =========================================================
    data = read_text(obj_a / "wyjście.txt")

    # =========================================================
    # ŻYŁA 2 — SYGNAŁ (STEROWANIE)
    # =========================================================
    signal_txt = read_text(obj_a / "sygnał.txt")
    try:
        signal = int(signal_txt)
    except:
        signal = 1  # domyślnie: przepuść

    if signal <= 0:
        log(f"[LINIA] SYGNAŁ={signal} → STOP (B nieodpalony)")
        return

    # =========================================================
    # ŻYŁA 3 — ŚCIEŻKA (INFO / routing przyszłościowy)
    # =========================================================
    path_flag = read_text(obj_a / "ścieżka.txt")
    if path_flag:
        log(f"[LINIA] ŚCIEŻKA={path_flag}")

    # =========================================================
    # PRZENIESIENIE DANYCH A → B
    # =========================================================
    path_in_b = obj_b / "wejście.txt"
    if not path_in_b.exists():
        log("[LINIA ERROR] B nie ma wejście.txt — STOP")
        return

    atomic_write(path_in_b, data)
    log("[LINIA] Dane A → B OK")

    # =========================================================
    # START OBIEKTU B
    # =========================================================
    run_object_start(obj_b)

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
