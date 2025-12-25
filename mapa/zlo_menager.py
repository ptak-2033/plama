import os
import time
import subprocess
from pathlib import Path
import sys

base_dir = Path(__file__).resolve().parent

# folder zlo
folder = base_dir / "zlo"

# okno startowe
okno_folder = base_dir / "okna_startowe"
okno_start = okno_folder / "start.py"

# auto_start
auto_start_dir = base_dir / "auto_start"
auto_procesy = []

# lista plików zło
pliki = sorted([p for p in folder.iterdir() if p.suffix == ".py"])


def start_auto_start():
    if not auto_start_dir.exists():
        print("[zlo_manager] Brak folderu auto_start")
        return

    for podfolder in auto_start_dir.iterdir():
        if not podfolder.is_dir():
            continue

        dodaj_py = podfolder / "dodaj.py"
        if dodaj_py.exists():
            print(f"[zlo_manager] Auto-start: {podfolder.name}/dodaj.py")
            proc = subprocess.Popen(
                [sys.executable, str(dodaj_py)],
                cwd=str(podfolder)
            )
            auto_procesy.append(proc)


def stop_auto_start():
    for proc in auto_procesy:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


# --- funkcja odpalenia okna startowego (raz) ---
def start_okno_startowe():
    if not okno_start.exists():
        print("[zlo_manager] Brak start.py w okna_startowe")
        return

    print("[zlo_manager] Odpalam okno startowe (raz)")
    subprocess.Popen(
        [sys.executable, str(okno_start)],
        cwd=str(okno_folder)
    )


# --- START SYSTEMU ---
start_okno_startowe()
start_auto_start()

try:
    while True:
        for plik in pliki:
            print(f"[zlo_manager] Odpalam {plik.name}")
            subprocess.Popen([sys.executable, str(plik)])
            time.sleep(0.5)
except KeyboardInterrupt:
    print("[zlo_manager] Zamknięcie mapy")
    stop_auto_start()
    sys.exit(0)
