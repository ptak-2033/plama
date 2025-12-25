import sys
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

BASE_DIR = Path(__file__).resolve().parent
NAPISY_DIR = BASE_DIR / "napisy"


def scan_processes():
    procs = []
    if not NAPISY_DIR.exists():
        return procs

    for f in NAPISY_DIR.iterdir():
        if f.is_dir() and f.name.isdigit():
            p = f / "proces.py"
            if p.exists():
                procs.append((int(f.name), p))

    procs.sort(key=lambda x: x[0])
    return [p for _, p in procs]


class ArrowWindow(QWidget):
    def __init__(self, text, callback, x, y, color="#222222", text_color="white", font_size=56):
        super().__init__()
        self.setFixedSize(120, 90)
        self.move(x, y)

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.FramelessWindowHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        btn = QPushButton(text, self)
        btn.setGeometry(0, 0, 120, 90)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: {text_color};
                font-size: {font_size}px;
                font-weight: 800;
                font-family: "Segoe UI";
                border: 2px solid #555;
                border-radius: 16px;
            }}
            QPushButton:hover {{
                background-color: #444444;
            }}
        """)
        btn.clicked.connect(callback)


class Controller:
    def __init__(self):
        self.processes = scan_processes()
        self.index = 0
        self.current_proc = None

    def run(self):
        if not self.processes:
            return

        if self.current_proc and self.current_proc.poll() is None:
            self.current_proc.kill()  # 🔪 ubij starego

        self.current_proc = subprocess.Popen(
            [sys.executable, str(self.processes[self.index])],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def next(self):
        self.index = (self.index + 1) % len(self.processes)
        self.run()

    def prev(self):
        self.index = (self.index - 1) % len(self.processes)
        self.run()


def confirm_exit():
    box = QMessageBox()
    box.setWindowTitle("Ej, chwila")
    box.setText("Na pewno opuszczasz samouczek?")
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.No)

    if box.exec_() == QMessageBox.Yes:
        app.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    ctrl = Controller()
    ctrl.run()  # 🔥 odpala pierwszy proces od razu

    screen = app.primaryScreen().geometry()
    cy = screen.height() // 2

    left = ArrowWindow("<", ctrl.prev, 30, cy - 45, color="#1f7a1f", font_size=64)
    right = ArrowWindow(">", ctrl.next, screen.width() - 150, cy - 45, color="#1f7a1f", font_size=64)

    exitw = ArrowWindow(
        "X",
        confirm_exit,
        30,
        screen.height() - 130,
        color="#7a1f1f",
        font_size=48
    )

    left.show()
    right.show()
    exitw.show()

    sys.exit(app.exec_())
