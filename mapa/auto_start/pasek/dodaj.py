import sys
import shutil
import re
import os
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap
from PyQt5.QtCore import Qt, QRect, QTimer

# =========================
# 🔍 ROOT
# =========================
def find_root(start: Path):
    p = start
    while p != p.parent:
        if (p / "mapa").exists() and (p / "obiekty").exists():
            return p
        p = p.parent
    raise RuntimeError("Nie znaleziono root PLAMY")

BASE = Path(__file__).resolve().parent
ROOT = find_root(BASE)

MAPA_DIR = ROOT / "mapa"
SENSORY_DIR = MAPA_DIR / "sensory"
OBIEKTY_DIR = ROOT / "obiekty"

# =========================
# 📄 PLIKI
# =========================
SLOT_TXT   = BASE / "slot.txt"
STAN_TXT   = BASE / "stan.txt"
SYGNAL_TXT = BASE / "sygnał.txt"
LP2_TXT    = SENSORY_DIR / "2xlp.txt"

# =========================
# ⚙️ GUI
# =========================
SLOTS = 9
SIZE = 56
GAP = 8
PAD = 10

BG = QColor(15, 15, 15, 200)
SLOT_BG = QColor(35, 35, 35)
SEL = QColor(255, 255, 255)

IGNORES = shutil.ignore_patterns("__pycache__", ".git", ".idea")
RX_START = re.compile(r"^start\s*=\s*(-?\d+)\s+(-?\d+)", re.M)

# =========================
# 🧠 MAPA
# =========================
def next_obj_name():
    rx = re.compile(r"^dodany obiekt (\d+)$")
    max_n = 0
    OBIEKTY_DIR.mkdir(exist_ok=True)
    for p in OBIEKTY_DIR.iterdir():
        if p.is_dir():
            m = rx.match(p.name)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return f"dodany obiekt {max_n + 1}"

def write_xy(path: Path, x: int, y: int):
    content = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    line = f"xy={x} {y}\n"
    if "xy=" in content:
        content = re.sub(r"^xy=.*$", line.strip(), content, flags=re.M)
    else:
        content += "\n" + line
    path.write_text(content.strip() + "\n", encoding="utf-8")

# =========================
# 🪟 GUI
# =========================
class Pasek(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.selected = self.read_slot()
        self.slot_folders = {}
        self.icons = {}
        
        # Pamięć poprzednich współrzędnych, żeby wykryć zmianę w 2xlp.txt
        self.last_coords = None 
        self.last_signal_mtime = None
        if SYGNAL_TXT.exists():
            self.last_signal_mtime = SYGNAL_TXT.stat().st_mtime

        self.resize(PAD * 2 + SLOTS * SIZE + (SLOTS - 1) * GAP + 30, PAD * 2 + SIZE)
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, screen.height() - self.height() - 20)

        self.scan_folders()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(150)

    def read_slot(self):
        try:
            return int(SLOT_TXT.read_text().strip())
        except:
            SLOT_TXT.write_text("0")
            return 0

    def read_stan(self):
        if not STAN_TXT.exists():
            STAN_TXT.write_text("off")
        return STAN_TXT.read_text().strip()

    def toggle_stan(self):
        STAN_TXT.write_text("off" if self.read_stan() == "on" else "on")

    def tick(self):
        self.handle_logic() # Zmieniona nazwa dla jasności
        self.update()

    def scan_folders(self):
        self.slot_folders.clear()
        self.icons.clear()
        for f in BASE.iterdir():
            if f.is_dir() and not f.name.startswith((".", "__")):
                sf = f / "slot.txt"
                if sf.exists():
                    try:
                        s = int(sf.read_text().strip())
                        self.slot_folders[s] = f
                        icon = f / "ikona.png"
                        if icon.exists():
                            self.icons[s] = QPixmap(str(icon))
                    except:
                        pass

    def handle_logic(self):
        # --- CZĘŚĆ 1: SYGNAŁ (PRZYPISANIE SLOTU) ---
        if SYGNAL_TXT.exists():
            mtime = SYGNAL_TXT.stat().st_mtime
            if self.last_signal_mtime != mtime:
                self.last_signal_mtime = mtime
                new_folder = None
                for f in BASE.iterdir():
                    if f.is_dir() and not f.name.startswith((".", "__")):
                        if not (f / "slot.txt").exists():
                            new_folder = f
                            break
                if new_folder:
                    self.scan_folders()
                    if self.selected in self.slot_folders:
                        shutil.rmtree(self.slot_folders[self.selected])
                    shutil.copy2(SLOT_TXT, new_folder / "slot.txt")
                    self.scan_folders()

        # --- CZĘŚĆ 2: STAN ON + ZMIANA W 2XLP (DODAWANIE NA MAPĘ) ---
        if self.read_stan() == "on" and LP2_TXT.exists():
            try:
                txt = LP2_TXT.read_text(encoding="utf-8", errors="ignore")
                m = RX_START.search(txt)
                if m:
                    current_coords = (int(m.group(1)), int(m.group(2)))
                    
                    # Jeśli współrzędne w 2xlp.txt się zmieniły (np. ktoś kliknął w innym miejscu)
                    if self.last_coords is not None and self.last_coords != current_coords:
                        template = self.slot_folders.get(self.selected)
                        if template:
                            x, y = current_coords
                            name = next_obj_name()
                            dest = OBIEKTY_DIR / name
                            shutil.copytree(template, dest, ignore=IGNORES)
                            write_xy(dest / "mapa_dane.txt", x, y)
                    
                    self.last_coords = current_coords
            except:
                pass

    def slot_rect(self, i):
        return QRect(PAD + i * (SIZE + GAP), PAD, SIZE, SIZE)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(BG)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), 14, 14)

        for i in range(SLOTS):
            r = self.slot_rect(i)
            p.setBrush(SLOT_BG)
            p.setPen(QPen(Qt.black, 2))
            p.drawRoundedRect(r, 10, 10)
            if i == self.selected:
                p.setPen(QPen(SEL, 3))
                p.drawRoundedRect(r.adjusted(1,1,-1,-1), 10, 10)
            if i in self.icons:
                pix = self.icons[i].scaled(40, 40, Qt.KeepAspectRatio)
                p.drawPixmap(r.center().x()-20, r.center().y()-20, pix)

        sw = QRect(self.width() - 24, 14, 14, 14)
        p.setBrush(QColor(0,220,0) if self.read_stan()=="on" else QColor(120,120,120))
        p.drawEllipse(sw)
        p.end()

    def mousePressEvent(self, e):
        sw = QRect(self.width() - 24, 14, 14, 14)
        if sw.contains(e.pos()):
            self.toggle_stan()
            return
        for i in range(SLOTS):
            if self.slot_rect(i).contains(e.pos()):
                self.selected = i
                SLOT_TXT.write_text(str(i))
                self.scan_folders()
                return

if __name__ == "__main__":
    try:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    except:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    w = Pasek()
    w.show()
    sys.exit(app.exec_())