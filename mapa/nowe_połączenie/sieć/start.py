#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OBIEKTY_DIR = ROOT.parent.parent / "obiekty"
LISTA = ROOT / "lista.txt"


def read_lista():
    """
    Zwraca:
    A_id,
    [
      {
        "id": int,
        "sygnal": int,
        "impuls": "on/off"
      }
    ]
    """
    A_id = None
    B_list = []

    for line in LISTA.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split(";")]

        if parts[0] == "A":
            for p in parts:
                if p.startswith("id="):
                    A_id = int(p.split("=", 1)[1])

        if parts[0] == "B":
            data = {}
            for p in parts:
                if p.startswith("id="):
                    data["id"] = int(p.split("=", 1)[1])
                if p.startswith("sygnal="):
                    data["sygnal"] = int(p.split("=", 1)[1])
                if p.startswith("impuls="):
                    data["impuls"] = p.split("=", 1)[1].lower()
            B_list.append(data)

    return A_id, B_list


def find_object_by_id(obj_id: int) -> Path | None:
    for obj in OBIEKTY_DIR.iterdir():
        if not obj.is_dir():
            continue
        id_file = obj / "id.txt"
        if not id_file.exists():
            continue
        try:
            if int(id_file.read_text().strip()) == obj_id:
                return obj
        except ValueError:
            continue
    return None


def run_all_lines():
    for line in ROOT.iterdir():
        if not line.is_dir():
            continue
        start = line / "start.py"
        if start.exists():
            subprocess.Popen(
                [sys.executable, str(start)],
                cwd=str(line)
            )


def run_line_for_B(B_id: int):
    for line in ROOT.iterdir():
        if not line.is_dir():
            continue

        ab = line / "AB.txt"
        start = line / "start.py"

        if not ab.exists() or not start.exists():
            continue

        txt = ab.read_text(encoding="utf-8")
        if f"obiekt_B={B_id}" in txt:
            subprocess.Popen(
                [sys.executable, str(start)],
                cwd=str(line)
            )


def main():
    A_id, B_list = read_lista()
    if A_id is None:
        return

    obj_A = find_object_by_id(A_id)
    if obj_A is None:
        return

    signal_file = obj_A / "sygnał.txt"

    # brak sygnału = ogień na wszystko 🔥
    if not signal_file.exists():
        run_all_lines()
        return

    try:
        signal = int(signal_file.read_text().strip())
    except ValueError:
        return

    for B in B_list:
        if B["sygnal"] != signal:
            continue
        if B.get("impuls") != "on":
            continue

        run_line_for_B(B["id"])


if __name__ == "__main__":
    main()
