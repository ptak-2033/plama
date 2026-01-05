# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets

# ============================================================
# UTILS – TXT = ŹRÓDŁO PRAWDY
# ============================================================
def resolve_base_dir():
    try:
        return Path(__file__).resolve().parents[2]
    except Exception:
        return Path.cwd().resolve()

def find_tekst_dane(base):
    files = list(base.rglob("tekst_dane.txt"))
    if not files:
        raise FileNotFoundError("Brak tekst_dane.txt")
    return files[0]

def parse_cfg(txt):
    return txt.splitlines(True)

def get(lines, section, key, default=""):
    sec = None
    for l in lines:
        s = l.strip()
        if s.startswith("[") and s.endswith("]"):
            sec = s[1:-1].lower()
            continue
        if sec == section and "=" in s:
            k, v = s.split("=", 1)
            if k.strip().lower() == key:
                return v.split(";", 1)[0].strip()
    return default

def setv(lines, section, key, value):
    sec = None
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith("[") and s.endswith("]"):
            sec = s[1:-1].lower()
            continue
        if sec == section and "=" in s:
            k, _ = s.split("=", 1)
            if k.strip().lower() == key:
                lines[i] = f"{key} = {value}\n"
                return lines
    lines.append(f"\n[{section}]\n{key} = {value}\n")
    return lines

# ============================================================
# MONITOR PODGLĄDU
# ============================================================
class Monitor(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(300)

        self.label = QtWidgets.QLabel("TEKST", self)
        self.label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        self.opacity = QtWidgets.QGraphicsOpacityEffect(self.label)
        self.label.setGraphicsEffect(self.opacity)

        self.anim_in = QtCore.QPropertyAnimation(self.opacity, b"opacity")
        self.anim_out = QtCore.QPropertyAnimation(self.opacity, b"opacity")

        self.pos_x = "srodek"
        self.pos_y = "srodek"

    def resizeEvent(self, e):
        self.update_position()

    def update_position(self):
        r = self.rect()
        size = self.label.sizeHint()

        x = {
            "lewo": 10,
            "srodek": (r.width() - size.width()) // 2,
            "prawo": r.width() - size.width() - 10
        }[self.pos_x]

        y = {
            "gora": 10,
            "srodek": (r.height() - size.height()) // 2,
            "dol": r.height() - size.height() - 10
        }[self.pos_y]

        self.label.setGeometry(x, y, size.width(), size.height())

    def set_style(self, color, size):
        self.label.setStyleSheet(
            f"color:{color}; font-weight:700; font-size:{size}px;"
        )
        self.label.adjustSize()
        self.update_position()

    def set_position(self, x, y):
        self.pos_x = x
        self.pos_y = y
        self.update_position()

    def play(self, tin, hold, tout):
        self.anim_in.stop()
        self.anim_out.stop()

        self.anim_in.setDuration(int(tin * 1000))
        self.anim_in.setStartValue(0)
        self.anim_in.setEndValue(1)

        self.anim_out.setDuration(int(tout * 1000))
        self.anim_out.setStartValue(1)
        self.anim_out.setEndValue(0)

        self.anim_in.start()
        QtCore.QTimer.singleShot(
            int((tin + hold) * 1000),
            self.anim_out.start
        )

# ============================================================
# MAIN GUI
# ============================================================
class Editor(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.base = resolve_base_dir()
        self.file = find_tekst_dane(self.base)
        self.lines = parse_cfg(self.file.read_text(encoding="utf-8"))

        self.setWindowTitle("PLAMA — Tekst na ekranie")
        self.resize(1100, 650)

        root = QtWidgets.QHBoxLayout(self)
        left = QtWidgets.QVBoxLayout()
        right = QtWidgets.QVBoxLayout()
        root.addLayout(left, 0)
        root.addLayout(right, 1)

        def lbl(t):
            l = QtWidgets.QLabel(t)
            l.setStyleSheet("font-weight:600;")
            return l

        # ---------- KOLORY
        left.addWidget(lbl("Kolory"))
        self.btn_bg = QtWidgets.QPushButton("Tło")
        self.btn_fg = QtWidgets.QPushButton("Tekst")
        left.addWidget(self.btn_bg)
        left.addWidget(self.btn_fg)

        self.chk_bg_lock = QtWidgets.QCheckBox("Blokuj tło (kanał alfa)")
        left.addWidget(self.chk_bg_lock)

        self.bg_color = "#000000"
        self.fg_color = "#FFFFFF"

        self.btn_bg.clicked.connect(lambda: self.pick_color("bg"))
        self.btn_fg.clicked.connect(lambda: self.pick_color("fg"))
        self.chk_bg_lock.stateChanged.connect(self.apply_background)

        # ---------- ROZMIAR
        left.addWidget(lbl("Rozmiar tekstu"))
        self.s_font = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.s_font.setRange(10, 200)
        left.addWidget(self.s_font)
        self.l_font = QtWidgets.QLabel()
        left.addWidget(self.l_font)

        # ---------- ANIMACJA
        def slider(maxv):
            s = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            s.setRange(0, maxv)
            left.addWidget(s)
            l = QtWidgets.QLabel()
            left.addWidget(l)
            return s, l

        left.addWidget(lbl("Pojawianie"))
        self.s_in, self.l_in = slider(300)
        left.addWidget(lbl("Znikanie"))
        self.s_out, self.l_out = slider(300)
        left.addWidget(lbl("Czas na ekranie"))
        self.s_hold, self.l_hold = slider(600)

        # ---------- POZYCJA
        left.addWidget(lbl("Pozycja tekstu"))
        grid = QtWidgets.QGridLayout()
        self.pos_x = "srodek"
        self.pos_y = "srodek"

        mapa = [
            ("lewo","gora"), ("srodek","gora"), ("prawo","gora"),
            ("lewo","srodek"), ("srodek","srodek"), ("prawo","srodek"),
            ("lewo","dol"), ("srodek","dol"), ("prawo","dol"),
        ]

        for i,(x,y) in enumerate(mapa):
            b = QtWidgets.QPushButton("")
            b.setFixedSize(40,40)
            b.clicked.connect(lambda _, a=x, b=y: self.set_pos(a,b))
            grid.addWidget(b, i//3, i%3)

        left.addLayout(grid)

        # ---------- BUTTONY
        self.btn_test = QtWidgets.QPushButton("▶ TEST")
        self.btn_save = QtWidgets.QPushButton("💾 ZAPISZ")
        left.addWidget(self.btn_test)
        left.addWidget(self.btn_save)
        left.addStretch(1)

        # ---------- MONITOR
        self.monitor = Monitor()
        right.addWidget(self.monitor)

        self.btn_test.clicked.connect(self.test)
        self.btn_save.clicked.connect(self.save)

        self.s_font.valueChanged.connect(self.update_labels)
        self.s_in.valueChanged.connect(self.update_labels)
        self.s_out.valueChanged.connect(self.update_labels)
        self.s_hold.valueChanged.connect(self.update_labels)

        self.load()

    # ========================================================
    def update_labels(self):
        self.l_font.setText(f"{self.s_font.value()} px")
        self.l_in.setText(f"{self.s_in.value()/100:.2f} s")
        self.l_out.setText(f"{self.s_out.value()/100:.2f} s")
        self.l_hold.setText(f"{self.s_hold.value()/100:.2f} s")

    def apply_background(self):
        if self.chk_bg_lock.isChecked():
            self.monitor.setStyleSheet("background:transparent; border:none;")
        else:
            self.monitor.setStyleSheet(
                f"background:{self.bg_color}; border:2px solid #222;"
            )

    def pick_color(self, which):
        col = QtWidgets.QColorDialog.getColor()
        if not col.isValid():
            return
        if which == "bg":
            self.bg_color = col.name()
            self.apply_background()
        else:
            self.fg_color = col.name()

    def set_pos(self, x, y):
        self.pos_x = x
        self.pos_y = y
        self.monitor.set_position(x, y)

    # ---------- LOAD Z TXT
    def load(self):
        self.bg_color = get(self.lines, "wizualne", "kolor_okna", "#000000")
        self.fg_color = get(self.lines, "wizualne", "kolor_tekstu", "#FFFFFF")

        self.chk_bg_lock.setChecked(
            get(self.lines, "wizualne", "blokuj_tlo", "0") == "1"
        )

        self.s_font.setValue(int(get(self.lines, "wizualne", "rozmiar", "40")))
        self.s_in.setValue(int(float(get(self.lines, "animacja", "czas_pojawiania", "0.25")) * 100))
        self.s_out.setValue(int(float(get(self.lines, "animacja", "czas_znikania", "0.25")) * 100))
        self.s_hold.setValue(int(float(get(self.lines, "animacja", "czas_wyswietlania", "3")) * 100))

        self.pos_x = get(self.lines, "pozycja", "poziom", "srodek")
        self.pos_y = get(self.lines, "pozycja", "pion", "srodek")

        self.apply_background()
        self.monitor.set_style(self.fg_color, self.s_font.value())
        self.monitor.set_position(self.pos_x, self.pos_y)
        self.update_labels()

    # ---------- TEST
    def test(self):
        self.monitor.set_style(self.fg_color, self.s_font.value())
        self.monitor.set_position(self.pos_x, self.pos_y)
        self.monitor.play(
            self.s_in.value()/100,
            self.s_hold.value()/100,
            self.s_out.value()/100
        )

    # ---------- SAVE DO TXT
    def save(self):
        self.lines = setv(self.lines, "wizualne", "kolor_okna", self.bg_color)
        self.lines = setv(self.lines, "wizualne", "kolor_tekstu", self.fg_color)
        self.lines = setv(self.lines, "wizualne", "blokuj_tlo",
                          "1" if self.chk_bg_lock.isChecked() else "0")
        self.lines = setv(self.lines, "wizualne", "rozmiar", self.s_font.value())

        self.lines = setv(self.lines, "animacja", "czas_pojawiania", self.s_in.value()/100)
        self.lines = setv(self.lines, "animacja", "czas_znikania", self.s_out.value()/100)
        self.lines = setv(self.lines, "animacja", "czas_wyswietlania", self.s_hold.value()/100)

        self.lines = setv(self.lines, "pozycja", "poziom", self.pos_x)
        self.lines = setv(self.lines, "pozycja", "pion", self.pos_y)

        self.file.write_text("".join(self.lines), encoding="utf-8")
        QtWidgets.QMessageBox.information(self, "OK", "Zapisane 🔥")

# ============================================================
def main():
    app = QtWidgets.QApplication(sys.argv)
    w = Editor()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
