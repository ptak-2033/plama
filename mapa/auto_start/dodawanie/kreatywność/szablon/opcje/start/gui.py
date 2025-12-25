import sys
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer


# kolory
LIGHT_GREEN = "#a8ffb0"
BRIGHT_GREEN = "#00ff00"
RED = "#ff3333"


class Launcher(QWidget):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app

        # === OKNO OVERLAY ===
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowStaysOnTopHint |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.resize(320, 120)
        screen = app.primaryScreen().geometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )

        # === LABEL ===
        self.label = QLabel("Uruchamiam…", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.resize(self.size())
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {LIGHT_GREEN};
                font-size: 28px;
                font-weight: bold;
            }}
        """)

        # === FADE IN ===
        self.setWindowOpacity(0.0)
        self.anim_in = QPropertyAnimation(self, b"windowOpacity")
        self.anim_in.setDuration(400)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)

        self.show()
        self.anim_in.start()

        QTimer.singleShot(200, self.try_launch)

    def try_launch(self):
        target = Path(__file__).resolve().parents[2] / "start.py"
        if not target.exists():
            self.fail("Brak start.py")
            return

        # pythonw = zero konsoli
        pythonw = Path(sys.executable).with_name("pythonw.exe")

        subprocess.Popen(
            [str(pythonw), str(target)],
            cwd=str(target.parent),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        # zmiana napisu
        self.label.setText("START")
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {BRIGHT_GREEN};
                font-size: 36px;
                font-weight: bold;
            }}
        """)

        # === ZNIKA PO 1s ===
        QTimer.singleShot(1000, self.fade_out)

    def fade_out(self):
        self.anim_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_out.setDuration(400)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()

    def closeEvent(self, event):
        self.app.quit()

    def fail(self, msg: str):
        self.label.setText(f"BŁĄD\n{msg}")
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {RED};
                font-size: 18px;
                font-weight: bold;
            }}
        """)
        QTimer.singleShot(2000, self.close)


def main():
    app = QApplication(sys.argv)
    Launcher(app)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
