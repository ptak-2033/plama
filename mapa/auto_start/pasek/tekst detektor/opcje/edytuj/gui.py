import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QLabel
)
from PyQt5.QtCore import Qt

BASE_DIR = Path(__file__).resolve().parents[2]
TEKST_PATH = BASE_DIR / "tekst.txt"

class TekstGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("tekst detektor")
        self.setFixedSize(420, 500)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #dddddd;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                padding: 6px;
                border-radius: 6px;
            }
            QPushButton {
                background-color: #2f2f2f;
                border: 1px solid #444;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("TEKSTY DO WYKRYWANIA")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        self.inner = QWidget()
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setSpacing(6)
        self.scroll.setWidget(self.inner)

        layout.addWidget(self.scroll)

        btns = QHBoxLayout()
        self.btn_add = QPushButton("+")
        self.btn_save = QPushButton("ZAPISZ")
        self.btn_exit = QPushButton("✕")

        self.btn_add.setFixedWidth(40)
        self.btn_exit.setFixedWidth(40)

        btns.addWidget(self.btn_add)
        btns.addStretch()
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_exit)

        layout.addLayout(btns)

        self.inputs = []

        self.btn_add.clicked.connect(self.add_line)
        self.btn_save.clicked.connect(self.save)
        self.btn_exit.clicked.connect(self.close)

        self.load()

    def load(self):
        if TEKST_PATH.exists():
            for line in TEKST_PATH.read_text(encoding="utf-8").splitlines():
                self.add_line(line)

    def add_line(self, text=""):
        if isinstance(text, bool):
            text = ""
        inp = QLineEdit(str(text))
        inp.setPlaceholderText("jedna linia = jeden wzorzec")
        self.inner_layout.addWidget(inp)
        self.inputs.append(inp)


    def save(self):
        lines = [
            i.text().strip()
            for i in self.inputs
            if i.text().strip()
        ]
        TEKST_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = TekstGUI()

    # centrowanie
    screen = app.primaryScreen().geometry()
    gui.move(
        screen.center().x() - gui.width() // 2,
        screen.center().y() - gui.height() // 2
    )

    gui.show()
    sys.exit(app.exec_())
