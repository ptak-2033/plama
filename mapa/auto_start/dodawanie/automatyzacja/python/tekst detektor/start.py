import os
import subprocess
import time
import threading
import hashlib
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))

TIMEOUT = 30          # max czas na proces.py
STOP_CHECK = 0.2      # co ile sekund sprawdzać stop.txt

LOG_PATH = os.path.join(ROOT, "log.txt")


def wczytaj(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""


def zapisz(path, txt):
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)


def log(txt):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {txt}\n")
    except:
        pass


def hash_txt(txt):
    return hashlib.sha256(txt.encode("utf-8", errors="ignore")).hexdigest()


def ustaw_proces(stan):
    mapa = os.path.join(ROOT, "mapa_dane.txt")
    if not os.path.exists(mapa):
        log("WARN: brak mapa_dane.txt (nie ustawiam proces=...)")
        return

    lines = wczytaj(mapa).split("\n")
    out = []
    found = False

    for l in lines:
        if l.startswith("proces="):
            out.append(f"proces={stan}")
            found = True
        else:
            out.append(l)

    if not found:
        out.append(f"proces={stan}")

    zapisz(mapa, "\n".join(out))
    log(f"STATUS: proces={stan}")


def uruchom_nastepna_linie(line_id):
    linie_dir = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "linie")
    if not os.path.exists(linie_dir):
        log("WARN: brak folderu linie/ (nie uruchamiam następnej linii)")
        return

    for d in os.listdir(linie_dir):
        p = os.path.join(linie_dir, d)
        if not os.path.isdir(p):
            continue

        id_path = os.path.join(p, "L_id.txt")
        if not os.path.exists(id_path):
            continue

        if wczytaj(id_path).strip() == line_id:
            start = os.path.join(p, "start.py")
            if os.path.exists(start):
                log(f"CHAIN: uruchamiam następną linię id={line_id} -> {start}")

                exe = sys.executable
                if sys.platform.startswith("win"):
                    exe = Path(exe).with_name("pythonw.exe")
                    subprocess.Popen(
                        [str(exe), start],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    subprocess.Popen([exe, start])

            else:
                log(f"WARN: znaleziono linię id={line_id}, ale brak start.py w {p}")
            return

    log(f"WARN: nie znaleziono linii o id={line_id} w linie/")

def monitor_stop(proc):
    stop_path = os.path.join(ROOT, "stop.txt")
    last_hash = hash_txt(wczytaj(stop_path))

    while True:
        time.sleep(STOP_CHECK)

        current = wczytaj(stop_path)
        current_hash = hash_txt(current)

        if current_hash != last_hash:
            # 🛑 STOP NATYCHMIAST
            log("STOP: wykryto zmianę w stop.txt -> KILL proces.py i exit")
            try:
                if proc.poll() is None:
                    proc.kill()
                    log("STOP: proces.py killed")
            except:
                log("STOP: nie udało się zabić procesu (albo już nie żył)")

            ustaw_proces("off")
            zapisz(
                os.path.join(ROOT, "wyjście.txt"),
                "STOP: wykryto zmianę w stop.txt"
            )
            os._exit(0)  # twarde wyjście


def main():
    try:
        # 🧼 reset loga na start sesji
        zapisz(LOG_PATH, "=== START SESJI ===\n")
        log("start.py uruchomiony")

        ustaw_proces("on")

        proc_path = os.path.join(ROOT, "proces.py")
        if not os.path.exists(proc_path):
            log("ERROR: brak proces.py")
            ustaw_proces("error")
            return

        log(f"RUN: python {proc_path}")
        proc = subprocess.Popen(
    ["python", proc_path],
    creationflags=subprocess.CREATE_NO_WINDOW
)

        # 👁️ watcher STOP
        t = threading.Thread(target=monitor_stop, args=(proc,), daemon=True)
        t.start()
        log("WATCHER: monitor_stop aktywny")

        try:
            proc.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            log(f"LAG: proces.py nie zakończył się w {TIMEOUT}s -> KILL")
            ustaw_proces("lag")
            try:
                proc.kill()
            except:
                pass
            zapisz(
                os.path.join(ROOT, "wyjście.txt"),
                f"LAG: proces.py nie zakończył się w {TIMEOUT}s"
            )
            return

        rc = proc.returncode
        log(f"EXIT: proces.py returncode={rc}")

        if rc != 0:
            ustaw_proces("error")
            zapisz(
                os.path.join(ROOT, "wyjście.txt"),
                f"BŁĄD: proces.py returncode={rc}"
            )
            log("ERROR: proces.py zakończony błędem")
            return

        # ✅ sukces
        ustaw_proces("old")
        log("SUKCES: proces.py zakończony poprawnie")

        nxt_path = os.path.join(ROOT, "następny.txt")
        if os.path.exists(nxt_path):
            nxt = wczytaj(nxt_path).strip()
            if nxt:
                log(f"NEXT: w następny.txt jest id={nxt}")
                uruchom_nastepna_linie(nxt)
            else:
                log("NEXT: następny.txt pusty (brak chain)")
        else:
            log("NEXT: brak następny.txt (brak chain)")

    except Exception as e:
        zapisz(
            os.path.join(ROOT, "wyjście.txt"),
            f"BŁĄD START: {e}"
        )
        try:
            log(f"FATAL: wyjątek w start.py -> {e}")
        except:
            pass
        ustaw_proces("error")


if __name__ == "__main__":
    main()
