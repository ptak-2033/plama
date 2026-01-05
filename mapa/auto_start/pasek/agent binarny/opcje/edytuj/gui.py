import sys
import subprocess
from pathlib import Path
from PyQt5.QtCore import Qt, QFileSystemWatcher, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
)
from PyQt5.QtGui import QColor


class FileSection(QWidget):
    def __init__(self, title, file_path: Path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setObjectName("fileSection")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        header = QLabel(title)
        header.setObjectName("sectionLabel")
        layout.addWidget(header)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText(str(self.file_path))
        self.editor.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.editor)

        self.setLayout(layout)
        self.load_file()

    def load_file(self):
        if self.file_path.exists():
            try:
                txt = self.file_path.read_text(encoding="utf-8")
            except:
                txt = self.file_path.read_text(errors="replace")
            self.editor.setPlainText(txt)

    def get_text(self):
        return self.editor.toPlainText()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Lokalizacja bazowa
        current_file = Path(__file__).resolve()
        base_dir = current_file.parents[2]

        self.config_path = base_dir / "konfiguracja.txt"
        self.instrukcje_path = base_dir / "instrukcje.txt"
        self.wejscie_path = base_dir / "wejście.txt"
        self.wyjscie_path = base_dir / "wyjście.txt"
        self.start_script_path = base_dir / "start.py"

        central = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # GÓRNA BELKA
        top = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")

        self.start_btn.setObjectName("startButton")
        self.stop_btn.setObjectName("stopButton")

        top.addWidget(self.start_btn)
        top.addWidget(self.stop_btn)
        top.addStretch()
        main_layout.addLayout(top)

        # GŁÓWNY PODZIAŁ: LEWO KOLUMNA, PRAWO KONFIG
        body = QHBoxLayout()

        # LEWA KOLUMNA (trzy sekcje JEDEN POD DRUGIM)
        left = QVBoxLayout()

        self.instrukcje_section = FileSection("instrukcje.txt", self.instrukcje_path)
        self.wejscie_section = FileSection("wejście.txt", self.wejscie_path)
        self.wyjscie_section = FileSection("wyjście.txt", self.wyjscie_path)

        left.addWidget(self.instrukcje_section)
        left.addWidget(self.wejscie_section)
        left.addWidget(self.wyjscie_section)

        # GLOBALNE ZASTOSUJ WSZYSTKO
        self.apply_all_btn = QPushButton("ZASTOSUJ WSZYSTKO")
        self.apply_all_btn.setObjectName("applyAllButton")
        left.addWidget(self.apply_all_btn)

        body.addLayout(left, stretch=4)

        # PRAWA KOLUMNA – WĄSKA, CIĄGNIĘTA DO SAMEGO DOŁU
        right = QVBoxLayout()
        self.config_section = FileSection("konfiguracja.txt", self.config_path)
        right.addWidget(self.config_section)
        body.addLayout(right, stretch=1)

        main_layout.addLayout(body)

        central.setLayout(main_layout)
        self.setCentralWidget(central)

        self._apply_theme()

        # ZIELONY OVERLAY "ZAPISANO"
        self.saved_label = QLabel("ZAPISANO")
        self.saved_label.setStyleSheet("""
            color: #00ff88;
            font-size: 26pt;
            font-weight: bold;
            background-color: rgba(0,0,0,160);
            padding: 20px;
            border-radius: 14px;
        """)
        self.saved_label.setAlignment(Qt.AlignCenter)
        self.saved_label.setVisible(False)
        self.saved_label.setParent(self)

        # WATCHER
        self.watcher = QFileSystemWatcher(self)
        self._setup_watcher()
        self.watcher.fileChanged.connect(self.on_file_changed)

        # SYGNAŁY
        self.start_btn.clicked.connect(self.start_process)
        self.stop_btn.clicked.connect(self.stop_process)
        self.apply_all_btn.clicked.connect(self.apply_all)

        self.resize(1500, 900)
        self.setWindowOpacity(0.93)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

    # POZYCJA OVERLAY
    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self.saved_label.resize(300, 100)
        self.saved_label.move((w - 300) // 2, (h - 100) // 2)

    # STYL
    def _apply_theme(self):
        styles = """
        QMainWindow { background-color: rgba(5, 10, 16, 220); }
        QWidget { color: #e8f5e9; font-family: Segoe UI; font-size: 11pt; }
        QTextEdit {
            background-color: rgba(10, 18, 26, 230);
            border: 1px solid rgba(0,255,128,120);
            border-radius: 8px;
            padding: 6px;
        }
        QLabel#sectionLabel { font-weight: 600; }
        QPushButton { border-radius: 10px; padding: 6px 14px; }
        QPushButton#startButton { background-color: #00c853; border: 1px solid #d4af37; }
        QPushButton#stopButton { background-color: #c62828; border: 1px solid #ff8a65; }
        QPushButton#applyAllButton {
            background-color: #f9a825;
            border: 2px solid #d4af37;
            font-weight: bold;
            font-size: 13pt;
            padding: 10px;
        }
        QWidget#fileSection {
            background-color: rgba(12,20,28,235);
            border-radius: 12px;
            border: 1px solid rgba(0,255,160,90);
        }
        """
        self.setStyleSheet(styles)

    # WATCHER
    def _setup_watcher(self):
        self.watcher.removePaths(self.watcher.files())
        lst = [self.config_path, self.instrukcje_path, self.wejscie_path, self.wyjscie_path]
        for p in lst:
            p.touch(exist_ok=True)
            self.watcher.addPath(str(p))

    def on_file_changed(self, path):
        p = Path(path)
        if p == self.config_path: self.config_section.load_file()
        elif p == self.instrukcje_path: self.instrukcje_section.load_file()
        elif p == self.wejscie_path: self.wejscie_section.load_file()
        elif p == self.wyjscie_path: self.wyjscie_section.load_file()

    # ZAPIS
    def apply_all(self):
        try:
            self.config_path.write_text(self.config_section.get_text(), encoding="utf-8")
            self.instrukcje_path.write_text(self.instrukcje_section.get_text(), encoding="utf-8")
            self.wejscie_path.write_text(self.wejscie_section.get_text(), encoding="utf-8")
            self.wyjscie_path.write_text(self.wyjscie_section.get_text(), encoding="utf-8")

            self.saved_label.setVisible(True)
            QTimer.singleShot(1000, lambda: self.saved_label.setVisible(False))

        except Exception as e:
            print("Błąd zapisu:", e)

    # START/STOP
    def start_process(self):
        if self.start_script_path.exists():
            subprocess.Popen([sys.executable, str(self.start_script_path)],
                             cwd=str(self.start_script_path.parent))

    def stop_process(self):
        pass


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
