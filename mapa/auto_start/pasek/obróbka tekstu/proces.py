# proces_pipeline.py — wersja PROCES
# zamienia twojego STARTA na prawdziwy proces wykonywany przez start.py

import subprocess, time, sys, tempfile, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

FILE_WEJSCIE = ROOT / "wejście.txt"
FILE_WYJSCIE = ROOT / "wyjście.txt"
FILE_NUMER   = ROOT / "numer.txt"
TRYBY_DIR    = ROOT / "tryby"
TEKST_FILE   = TRYBY_DIR / "tekst.txt"

MAX_WAIT = 60


def atomic_write(path: Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=str(path.parent))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(data)
    os.replace(tmp, str(path))


def read_numbers():
    if not FILE_NUMER.exists():
        return []
    raw = FILE_NUMER.read_text(encoding="utf-8", errors="ignore").strip()
    if not raw:
        return []
    nums = []
    for p in raw.replace(" ", "").split(","):
        if p.isdigit():
            nums.append(int(p))
    return nums


def find_script_for_number(num: int):
    """
    Znajduje plik trybu zaczynający się od numeru.
    Obsługuje nazwy typu:
    1 nazwa.py
    1_nazwa.py
    1-nazwa.py
    1.nazwa.py
    """
    for f in TRYBY_DIR.iterdir():
        if f.suffix.lower() != ".py":
            continue

        stem = (
            f.stem.replace(".", " ")
                  .replace("_", " ")
                  .replace("-", " ")
        )

        parts = stem.split(" ", 1)

        if parts[0].isdigit() and int(parts[0]) == num:
            return f

    return None



def main():

    # -- przygotuj tekst.txt z wejście.txt --
    if not FILE_WEJSCIE.exists():
        atomic_write(FILE_WYJSCIE, "❌ Brak wejście.txt")
        return

    wej = FILE_WEJSCIE.read_text(encoding="utf-8", errors="ignore")
    atomic_write(TEKST_FILE, wej)

    # -- pobierz pipeline trybów --
    pipeline = read_numbers()
    if not pipeline:
        atomic_write(FILE_WYJSCIE, "❌ numer.txt pusty")
        return

    # -- wykonuj tryby po kolei --
    for num in pipeline:

        script = find_script_for_number(num)

        if not script:
            atomic_write(FILE_WYJSCIE, f"❌ brak trybu zaczynającego się od {num}")
            return

        try:
            proc = subprocess.Popen([sys.executable, str(script)])
        except Exception as e:
            atomic_write(FILE_WYJSCIE, f"❌ błąd przy starcie trybu: {e}")
            return

        t0 = time.time()
        while True:
            if proc.poll() is not None:
                break
            if time.time() - t0 > MAX_WAIT:
                atomic_write(FILE_WYJSCIE, "⏳ timeout trybu")
                return
            time.sleep(0.1)

    # -- pipeline zakończony → wyjście.txt --
    final = TEKST_FILE.read_text(encoding="utf-8", errors="ignore")
    atomic_write(FILE_WYJSCIE, final)



if __name__ == "__main__":
    main()
