from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QCheckBox, QLabel, QFrame
)
from PyQt5.QtGui import QFont, QColor, QPalette
from PyQt5.QtCore import Qt
from pathlib import Path
import sys


def find_tryby_root():
    p = Path(__file__).resolve().parent
    for _ in range(12):
        if (p / "tryby").exists():
            return p
        p = p.parent
    raise RuntimeError("❌ Nie znaleziono folderu 'tryby'!")


ROOT = find_tryby_root()
TRYBY_DIR = ROOT / "tryby"
FILE_NUMER = ROOT / "numer.txt"


def load_tryby():
    entries = []
    for f in TRYBY_DIR.iterdir():
        if f.suffix.lower() in (".py", ".pu"):
            name = f.stem
            parts = (
                name.replace(".", " ")
                    .replace("_", " ")
                    .replace("-", " ")
                    .split(" ", 1)
            )
            if parts[0].isdigit():
                num = int(parts[0])
                label = parts[1].upper()
                entries.append((num, label))

    entries.sort(key=lambda x: x[0])
    return entries


def load_selected():
    if FILE_NUMER.exists():
        txt = FILE_NUMER.read_text(encoding="utf-8").strip()
        if txt:
            return {int(x) for x in txt.split(",") if x.isdigit()}
    return set()


# --------------------------------------------------
#  MOBILNY KAFEL – JEDEN TRYB
# --------------------------------------------------

class TrybTile(QFrame):
    def __init__(self, num, label, callback):
        super().__init__()
        self.num = num

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: #E5E5E5;
                border-radius: 10px;
                padding: 12px;
            }
        """)

        self.cb = QCheckBox(label)
        self.cb.setFont(QFont("Arial", 15))
        self.cb.stateChanged.connect(self.update_color)
        self.cb.stateChanged.connect(callback)

        layout = QVBoxLayout(self)
        layout.addWidget(self.cb)

    def set_checked(self, state):
        self.cb.setChecked(state)
        self.update_color()

    def is_checked(self):
        return self.cb.isChecked()

    def update_color(self):
        if self.cb.isChecked():
            self.setStyleSheet("""
                QFrame {
                    background: #9EEA8B;
                    border-radius: 10px;
                    padding: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: #E5E5E5;
                    border-radius: 10px;
                    padding: 12px;
                }
            """)


# --------------------------------------------------
#  GŁÓWNE OKNO
# --------------------------------------------------

class TrybyWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("TRYBY OBRÓBKI TEKSTU")
        self.setMinimumWidth(420)

        pal = self.palette()
        pal.setColor(QPalette.Window, QColor("#D0D0D0"))  # jasnoszare tło
        self.setPalette(pal)

        self.tiles = {}
        self.entries = load_tryby()
        selected = load_selected()

        layout = QVBoxLayout()
        title = QLabel("<b>ZAZNACZ TRYBY:</b>")
        title.setFont(QFont("Arial", 16))
        layout.addWidget(title)

        # kafelki trybów
        for num, label in self.entries:
            tile = TrybTile(num, label, self.save_selection)
            layout.addWidget(tile)
            self.tiles[num] = tile

        # wczytanie wcześniejszych zaznaczeń
        for num in selected:
            if num in self.tiles:
                self.tiles[num].set_checked(True)

        layout.addStretch()
        self.setLayout(layout)

    def save_selection(self):
        selected = [str(num) for num, tile in self.tiles.items() if tile.is_checked()]
        FILE_NUMER.write_text(",".join(selected), encoding="utf-8")
        print("✔ zapisano:", ",".join(selected))


app = QApplication(sys.argv)
window = TrybyWindow()
window.show()
sys.exit(app.exec_())
