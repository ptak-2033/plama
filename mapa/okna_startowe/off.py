#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui


NEXT_SCRIPT = "samouczek/samouczek.py"
HELP_SCRIPT = "więcej/więcej.py"
EXIT_SCRIPT = "wyłączenie.py"


class LeftBar(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        base = Path(__file__).parent
        text_file = base / "tekst.txt"

        gui_title = "okno pomocnicze"
        gui_desc = ""

        if text_file.exists():
            lines = text_file.read_text(encoding="utf-8").splitlines()
            if lines:
                gui_title = lines[0]
                gui_desc = "\n".join(lines[1:])

        self.setWindowTitle(f"PLAMA/{gui_title}")
        self.setFixedSize(420, 680)

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )

        screen = QtWidgets.QApplication.primaryScreen()
        geo = screen.availableGeometry()
        margin = 16
        x = geo.left() + margin
        y = geo.top() + (geo.height() - self.height()) // 2
        self.move(x, y)

        root = QtWidgets.QFrame(self)
        root.setObjectName("root")
        root.setGeometry(0, 0, self.width(), self.height())

        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # ─── TOP BAR ─────────────────────────────
        top = QtWidgets.QHBoxLayout()

        title = QtWidgets.QLabel(gui_title)
        title.setObjectName("title")

        close_btn = QtWidgets.QPushButton("✕")
        close_btn.setObjectName("close_btn")
        close_btn.setFixedSize(32, 26)
        close_btn.clicked.connect(self.confirm_exit)

        top.addWidget(title)
        top.addStretch()
        top.addWidget(close_btn)
        layout.addLayout(top)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(sep)

        # ─── DESCRIPTION ─────────────────────────
        desc = QtWidgets.QLabel(gui_desc)
        desc.setWordWrap(True)
        desc.setObjectName("desc")
        layout.addWidget(desc, 2)

        # ─── OBRAZY (2x2, ~1/2 GUI) ──────────────
        images_grid = QtWidgets.QGridLayout()
        images_grid.setSpacing(10)

        row = col = 0
        for i in range(1, 5):
            img_path = base / f"{i}.png"
            if img_path.exists():
                lbl = QtWidgets.QLabel()
                lbl.setAlignment(QtCore.Qt.AlignCenter)
                pix = QtGui.QPixmap(str(img_path))
                lbl.setPixmap(
                    pix.scaled(
                        190, 140,
                        QtCore.Qt.KeepAspectRatio,
                        QtCore.Qt.SmoothTransformation
                    )
                )
                images_grid.addWidget(lbl, row, col)
                col += 1
                if col == 2:
                    col = 0
                    row += 1

        layout.addLayout(images_grid, 2)

        # ─── BUTTONS ─────────────────────────────
        buttons = QtWidgets.QHBoxLayout()

        help_btn = QtWidgets.QPushButton("WIĘCEJ")
        help_btn.setObjectName("help_btn")
        help_btn.clicked.connect(self.open_help)

        next_btn = QtWidgets.QPushButton("SAMOUCZEK")
        next_btn.setObjectName("next_btn")
        next_btn.clicked.connect(self.next_step)

        buttons.addWidget(help_btn)
        buttons.addWidget(next_btn)
        layout.addLayout(buttons)

        self.setStyleSheet(self.styles())

    # ─── LOGIKA ─────────────────────────────────
    def run_script(self, name):
        base = Path(__file__).resolve().parent
        path = base / name
        if path.exists():
            subprocess.Popen([sys.executable, str(path)], cwd=str(base))

    def open_help(self):
        self.run_script(HELP_SCRIPT)
        self.close()

    def next_step(self):
        self.run_script(NEXT_SCRIPT)
        self.close()

    # ─── MINI GUI EXIT ──────────────────────────
    def confirm_exit(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setFixedSize(340, 260)
        dialog.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool |
            QtCore.Qt.WindowStaysOnTopHint
        )

        root = QtWidgets.QFrame(dialog)
        root.setObjectName("root")
        root.setGeometry(0, 0, 340, 260)

        root.setStyleSheet("""
        #root {
            background-color: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #ffd6a0,
                stop:1 #ffb870
            );
            border-radius: 18px;
            border: 2px solid rgba(0,0,0,40);
        }
        """)

        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title = QtWidgets.QLabel("CZEKAJ")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("""
            color: black;
            font-size: 24px;
            font-weight: 900;
            letter-spacing: 1px;
        """)
        layout.addWidget(title)

        text = QtWidgets.QLabel(
            "Czy na pewno chcesz wyłączyć\nokno pomocnicze?"
        )
        text.setAlignment(QtCore.Qt.AlignCenter)
        text.setWordWrap(True)
        text.setStyleSheet("""
            color: black;
            font-size: 15px;
            font-weight: 600;
            line-height: 1.4;
        """)
        layout.addWidget(text)

        btn_yes = QtWidgets.QPushButton("TAK")
        btn_yes2 = QtWidgets.QPushButton("TAK I NIE POKAZUJ PONOWNIE")
        btn_no = QtWidgets.QPushButton("NIE")

        for btn in (btn_yes, btn_yes2, btn_no):
            btn.setMinimumHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 13px;
                    font-weight: 800;
                    border-radius: 12px;
                    padding: 8px;
                    background-color: rgba(0,0,0,0.75);
                    color: white;
                }
                QPushButton:hover {
                    background-color: rgba(0,0,0,0.9);
                }
            """)

        btn_yes.clicked.connect(lambda: (dialog.close(), self.close()))
        btn_yes2.clicked.connect(lambda: self._exit_and_close(dialog))
        btn_no.clicked.connect(dialog.close)

        layout.addWidget(btn_yes)
        layout.addWidget(btn_yes2)
        layout.addWidget(btn_no)

        dialog.exec_()

    def _exit_and_close(self, dialog):
        self.run_script(EXIT_SCRIPT)
        dialog.close()
        self.close()

    # ─── STYLES ─────────────────────────────────
    def styles(self):
        return """
        #root {
            background-color: qradialgradient(
                cx: 0.45, cy: 0.20, radius: 1.20,
                stop: 0 rgba(25, 35, 60, 255),
                stop: 1 rgba(10, 10, 14, 255)
            );
            border: 2px solid rgba(80, 190, 255, 210);
            border-radius: 18px;
        }

        QLabel {
            color: white;
            font-size: 15px;
            line-height: 1.5;
        }

        #title {
            font-size: 22px;
            font-weight: 900;
            letter-spacing: 1px;
        }

        #desc {
            font-size: 16px;
            line-height: 1.55;
            font-weight: 500;
        }

        QPushButton {
            border-radius: 14px;
            padding: 12px 14px;
            font-size: 13px;
            font-weight: 900;
            color: white;
        }

        #help_btn { background-color: #8a4bff; }
        #help_btn:hover { background-color: #6f3dd6; }

        #next_btn { background-color: #00c27a; }
        #next_btn:hover { background-color: #00a867; }

        #close_btn {
            background-color: #ff4b4b;
            font-size: 16px;
            font-weight: 900;
        }
        #close_btn:hover {
            background-color: #ff784e;
        }
        """


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = LeftBar()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
