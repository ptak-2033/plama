import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QTextEdit, QWidget, QVBoxLayout, QPushButton
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QFileSystemWatcher


class Notatnik(QWidget):
    def __init__(self):
        super().__init__()

        # === OKNO ===
        self.setWindowTitle("Notatnik")
        self.resize(700, 500)
        self.setWindowFlags(Qt.Window | Qt.Tool)

        # === ŚCIEŻKI (2 WARSTWY WYŻEJ) ===
        self.base_dir = Path(__file__).resolve().parents[2]
        self.wejscie = self.base_dir / "wejście.txt"
        self.wyjscie = self.base_dir / "wyjście.txt"
        self.kopia = self.base_dir / "kopia.txt"

        for f in (self.wejscie, self.wyjscie, self.kopia):
            f.touch(exist_ok=True)

        # === EDYTOR (TYLKO PODGLĄD + EDYCJA LOKALNA) ===
        self.text = QTextEdit()
        self.text.setFont(QFont("Consolas", 14))

        self.text.setStyleSheet("""
            QTextEdit {
                background-color: #0d1b2a;
                color: #e0e8ff;
                border: 2px solid #1b3a5c;
                border-radius: 10px;
                padding: 12px;
            }
        """)

        # === PRZYCISK ZAPISU ===
        self.btn_zapisz = QPushButton("ZAPISZ → ŚWIAT")
        self.btn_zapisz.clicked.connect(self.zapisz)
        self.btn_zapisz.setStyleSheet("""
            QPushButton {
                background-color: #1b3a5c;
                color: #e0e8ff;
                padding: 8px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #244b73;
            }
        """)

        # === LAYOUT ===
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(self.text)
        layout.addWidget(self.btn_zapisz)

        self.setStyleSheet("QWidget { background-color: #08121f; }")

        # === WATCHER (WEJŚCIE + WYJŚCIE) ===
        self.watcher = QFileSystemWatcher([
            str(self.wejscie),
            str(self.wyjscie),
        ])
        self.watcher.fileChanged.connect(self.wczytaj_z_pliku)

        # === PIERWSZY ODCZYT ===
        self.wczytaj_z_pliku()

    def wczytaj_z_pliku(self):
        # oba pliki mają mieć to samo — czytamy jeden
        if not self.wejscie.exists():
            return

        data = self.wejscie.read_text(encoding="utf-8")

        if data != self.text.toPlainText():
            self.text.blockSignals(True)
            self.text.setPlainText(data)
            self.text.blockSignals(False)

        # Qt bug — pilnujemy, żeby watcher nie zdechł
        for f in (self.wejscie, self.wyjscie):
            if str(f) not in self.watcher.files():
                self.watcher.addPath(str(f))

    def zapisz(self):
        data = self.text.toPlainText()

        # synchronizacja świata
        self.wejscie.write_text(data, encoding="utf-8")
        self.wyjscie.write_text(data, encoding="utf-8")
        self.kopia.write_text(data, encoding="utf-8")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    okno = Notatnik()
    okno.show()
    sys.exit(app.exec_())
