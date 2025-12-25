import sys
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

BASE_DIR = Path(__file__).resolve().parent
PLUS_IMG = BASE_DIR / "plus.png"
GUI_PY = BASE_DIR / "gui.py"

PLUS_SIZE = 96  # 👈 ROZMIAR PLUSA (px) – zmień jak chcesz

gui_proc = None  # 👈 trzymamy PID GUI


class PlusWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        pixmap = QPixmap(str(PLUS_IMG)).scaled(
            PLUS_SIZE,
            PLUS_SIZE,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.label = QLabel(self)
        self.label.setPixmap(pixmap)
        self.label.resize(pixmap.size())

        self.resize(pixmap.size())

        # 📍 prawy dolny róg
        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.width() - pixmap.width() - 24,
            screen.height() - pixmap.height() - 24
        )

    def mousePressEvent(self, event):
        global gui_proc

        if event.button() != Qt.LeftButton:
            return

        # 🔥 jeśli GUI działa → ZABIJAJ CAŁĄ GAŁĄŹ
        if gui_proc and gui_proc.poll() is None:
            try:
                import psutil
                p = psutil.Process(gui_proc.pid)
                for child in p.children(recursive=True):
                    child.kill()
                p.kill()
            except Exception:
                pass

            gui_proc = None
            return

        # 🚀 jeśli nie działa → odpal
        if GUI_PY.exists():
            gui_proc = subprocess.Popen(
                [sys.executable, str(GUI_PY)],
                cwd=str(BASE_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = PlusWindow()
    w.show()
    sys.exit(app.exec_())
