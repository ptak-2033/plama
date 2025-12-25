import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STOP = ROOT / "stop.txt"


def read_stop():
    try:
        return STOP.read_text(encoding="utf-8").strip()
    except:
        return ""


def write_stop(val: str):
    STOP.write_text(val, encoding="utf-8")


def main():
    val = read_stop()

    if val == "":
        # brak / pusty
        write_stop("0")
        return

    if val == "0":
        write_stop("1")
        return

    if val == "1":
        write_stop("0")
        return

    # cokolwiek innego → reset na 0
    write_stop("0")


if __name__ == "__main__":
    main()
