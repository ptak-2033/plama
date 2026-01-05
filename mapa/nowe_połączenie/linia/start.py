#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
from pathlib import Path
import datetime

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "sieć_log.txt"


def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        LOG.write_text(LOG.read_text(encoding="utf-8") + line, encoding="utf-8")
    except Exception:
        try:
            LOG.write_text(line, encoding="utf-8")
        except Exception:
            pass
    print(line, end="")


def main():
    log("=== START SIECI ===")

    for sub in ROOT.iterdir():
        if not sub.is_dir():
            continue

        # ⛔ pomijamy opcje
        if sub.name.lower() == "opcje":
            continue

        start_py = sub / "start.py"
        if not start_py.exists():
            continue

        try:
            subprocess.Popen(
                [sys.executable, str(start_py)],
                cwd=str(sub),
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            log(f"[SIEĆ] Odpalono: {sub.name}/start.py")
        except Exception as e:
            log(f"[SIEĆ ERROR] {sub.name}: {e}")

    log("=== KONIEC STARTU SIECI (fan-out) ===")


if __name__ == "__main__":
    main()
