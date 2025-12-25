# proces.py
import sys
from pathlib import Path
from PyQt5 import QtWidgets, QtCore

# =========================
# ŚCIEŻKI
# =========================
BASE = Path(__file__).parent
TXT = BASE / "wejście.txt"
CFG = BASE / "tekst_dane.txt"

# =========================
# CFG PARSER
# =========================
def get(lines, section, key, default=""):
    sec = None
    for l in lines:
        s = l.strip()
        if s.startswith("[") and s.endswith("]"):
            sec = s[1:-1].lower()
        elif sec == section and "=" in s:
            k, v = s.split("=", 1)
            if k.strip().lower() == key:
                return v.split(";", 1)[0].strip()
    return default

# =========================
# WCZYTANIE
# =========================
text = TXT.read_text(encoding="utf-8")
lines = CFG.read_text(encoding="utf-8").splitlines(True)

size = int(get(lines, "wizualne", "rozmiar", "40"))
fg = get(lines, "wizualne", "kolor_tekstu", "#00ff00")
bg_lock = get(lines, "wizualne", "blokuj_tlo", "1") == "1"

tin = float(get(lines, "animacja", "czas_pojawiania", "0.3"))
tout = float(get(lines, "animacja", "czas_znikania", "0.3"))
hold = float(get(lines, "animacja", "czas_wyswietlania", "3"))

pos_x = get(lines, "pozycja", "poziom", "srodek")
pos_y = get(lines, "pozycja", "pion", "srodek")

# =========================
# QT START
# =========================
app = QtWidgets.QApplication(sys.argv)

screen = app.primaryScreen().geometry()
sw, sh = screen.width(), screen.height()

# OKNO MUSI MIEĆ ROZMIAR EKRANU ❗
w = QtWidgets.QWidget()
w.setGeometry(0, 0, sw, sh)
w.setWindowFlags(
    QtCore.Qt.FramelessWindowHint |
    QtCore.Qt.Tool |
    QtCore.Qt.WindowStaysOnTopHint
)
w.setAttribute(QtCore.Qt.WA_TranslucentBackground, bg_lock)

# =========================
# LABEL
# =========================
label = QtWidgets.QLabel(text, w)
label.setStyleSheet(
    f"color:{fg}; font-size:{size}px; font-weight:700;"
)
label.adjustSize()

lw, lh = label.width(), label.height()
pad = 20

x = {
    "lewo": pad,
    "srodek": (sw - lw) // 2,
    "prawo": sw - lw - pad
}.get(pos_x, (sw - lw) // 2)

y = {
    "gora": pad,
    "srodek": (sh - lh) // 2,
    "dol": sh - lh - pad
}.get(pos_y, (sh - lh) // 2)

label.move(x, y)

# =========================
# ANIMACJA
# =========================
opacity = QtWidgets.QGraphicsOpacityEffect(label)
label.setGraphicsEffect(opacity)

anim_in = QtCore.QPropertyAnimation(opacity, b"opacity")
anim_in.setDuration(int(tin * 1000))
anim_in.setStartValue(0)
anim_in.setEndValue(1)

anim_out = QtCore.QPropertyAnimation(opacity, b"opacity")
anim_out.setDuration(int(tout * 1000))
anim_out.setStartValue(1)
anim_out.setEndValue(0)

# =========================
# RUN
# =========================
w.show()
anim_in.start()

QtCore.QTimer.singleShot(int((tin + hold) * 1000), anim_out.start)
QtCore.QTimer.singleShot(int((tin + hold + tout) * 1000), app.quit)

sys.exit(app.exec_())
