import pyttsx3
from pathlib import Path

# katalog, w którym jest ten plik .py
BASE_DIR = Path(__file__).resolve().parent

wejscie = BASE_DIR / "wejście.txt"
wyjscie = BASE_DIR / "wyjście.txt"

if not wejscie.exists():
    raise FileNotFoundError(f"Brak pliku: {wejscie}")

# wczytaj tekst
text = wejscie.read_text(encoding="utf-8")

# zapisz kopię
wyjscie.write_text(text, encoding="utf-8")

# syntezator mowy (Windows SAPI5)
engine = pyttsx3.init()
engine.setProperty("rate", 170)
engine.setProperty("volume", 1.0)

engine.say(text)
engine.runAndWait()
