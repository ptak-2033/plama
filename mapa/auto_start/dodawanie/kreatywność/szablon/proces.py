import time
import os
import hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
MAPA = os.path.join(ROOT, "mapa_dane.txt")
STOP = os.path.join(ROOT, "stop.txt")

STANY = ["on", "lag", "error"]
INTERVAL = 3

START_TIME = time.time()
MAX_TIME = 10  # sekundy


def wczytaj(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""


def hash_txt(txt):
    return hashlib.sha256(txt.encode("utf-8", errors="ignore")).hexdigest()


def ustaw_proces(stan):
    if not os.path.exists(MAPA):
        return

    lines = wczytaj(MAPA).split("\n")
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

    with open(MAPA, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


# =========================
# START
# =========================

stop_hash = hash_txt(wczytaj(STOP))
idx = 0

while True:
    # ⏱️ limit 10 sekund
    if time.time() - START_TIME >= MAX_TIME:
        break

    # 🛑 sprawdzaj STOP
    current_hash = hash_txt(wczytaj(STOP))
    if current_hash != stop_hash:
        break

    stan = STANY[idx % len(STANY)]
    ustaw_proces(stan)

    idx += 1
    time.sleep(INTERVAL)

# ciche wyjście – zero kolizji, zero dram 🎭
