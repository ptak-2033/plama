import sys
import os
import subprocess
import shutil
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QScrollArea, QGridLayout, QLabel,
    QFrame, QToolTip
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QPoint

TOOLTIP_STYLE = """
    QToolTip { 
        background-color: #1e1e1f; 
        color: #ffffff; 
        border: 2px solid #545454; 
        padding: 5px;
        font-family: 'Segoe UI', sans-serif;
    }
"""

# ===================== HOVER LABEL =====================

class HoverLabel(QLabel):
    def __init__(self, name, path, callback):
        super().__init__()
        self.name = name
        self.path = path
        self.callback = callback
        self.setFixedSize(60, 60)
        self.setCursor(Qt.PointingHandCursor)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 2px solid #373737; background: rgba(139,139,139,150);")

    def enterEvent(self, event):
        self.setStyleSheet("border: 3px solid #3de03d; background: rgba(139,139,139,200);")
        QToolTip.showText(self.mapToGlobal(QPoint(0, 40)), self.name, self)

    def leaveEvent(self, event):
        self.setStyleSheet("border: 2px solid #373737; background: rgba(139,139,139,150);")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.callback(self.path)

# ===================== ITEM WIDGET =====================

class ItemWidget(QFrame):
    def __init__(self, name, folder_path):
        super().__init__()
        self.name = name
        self.folder_path = folder_path
        self.setFixedSize(110, 110)
        self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet("""
            QFrame { 
                background-color: rgba(60,60,60,180); 
                border: 3px solid #373737; 
            }
        """)

        layout = QVBoxLayout(self)
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("border:none; background:transparent;")

        img_path = os.path.join(self.folder_path, "ikona.png")
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path).scaled(
                80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.icon_label.setPixmap(pixmap)
        else:
            self.icon_label.setText(self.name)
            self.icon_label.setStyleSheet("color:white; font-weight:bold;")

        layout.addWidget(self.icon_label)

    def enterEvent(self, event):
        self.setStyleSheet(
            "background-color: rgba(80,80,80,220); border:3px solid #3de03d;"
        )
        QToolTip.showText(self.mapToGlobal(QPoint(0, 0)), self.name, self)

    def leaveEvent(self, event):
        self.setStyleSheet(
            "background-color: rgba(60,60,60,180); border:3px solid #373737;"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.copy_to_pasek()
        elif event.button() == Qt.RightButton:
            self.run_script("pp.py")
        elif event.button() == Qt.MidButton:
            self.run_script("2xlp.py")

    def run_script(self, script_name):
        path = os.path.join(self.folder_path, script_name)
        if os.path.exists(path):
            subprocess.Popen(["python", path], cwd=self.folder_path, shell=True)

    # ===================== KOPIOWANIE =====================

    def copy_to_pasek(self):
        app = QApplication.instance()
        main = app.activeWindow()

        main.show_blocker("Kopiowanie...")

        src = self.folder_path
        auto_start = os.path.abspath(os.path.join(main.base_dir, "..", ".."))

        dst = os.path.join(
            auto_start,
            "pasek",
            os.path.basename(self.folder_path)
        )

        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)

            shutil.copytree(src, dst)

            # ===== CZEKA AŻ FOLDER SIĘ SKOPIUJE =====
            while not os.path.exists(dst):
                time.sleep(0.05)

            # ===== TOGGLE sygnał.txt =====
            pasek_dir = os.path.join(auto_start, "pasek")
            sygnal = os.path.join(pasek_dir, "sygnał.txt")

            if not os.path.exists(sygnal):
                with open(sygnal, "w", encoding="utf-8") as f:
                    f.write("1")
            else:
                with open(sygnal, "r", encoding="utf-8") as f:
                    val = f.read().strip()

                if val == "1":
                    new_val = "0"
                else:
                    new_val = "1"

                with open(sygnal, "w", encoding="utf-8") as f:
                    f.write(new_val)

        except Exception as e:
            print(f"[ERROR] {e}")

        main.hide_blocker()

# ===================== MAIN GUI =====================

class InventoryBrowser(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.all_items = []

        self.initUI()
        self.load_categories()

    def initUI(self):
        self.resize(950, 750)

        self.main_frame = QFrame(self)
        self.main_frame.setGeometry(0, 0, 950, 750)
        self.main_frame.setStyleSheet("""
            background-color: rgba(40,40,40,230);
            border-radius: 10px;
            border: 2px solid #1a1a1a;
        """)

        layout = QVBoxLayout(self.main_frame)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Wyszukaj...")
        self.search_bar.textChanged.connect(self.filter_items)
        layout.addWidget(self.search_bar)

        self.cat_layout = QHBoxLayout()
        layout.addLayout(self.cat_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:transparent; border:none;")

        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container)

        layout.addWidget(self.scroll)

    def show_blocker(self, text="Kopiowanie..."):
        self.blocker = QFrame(self)
        self.blocker.setGeometry(0, 0, self.width(), self.height())
        self.blocker.setStyleSheet("background-color: rgba(0,0,0,180);")

        label = QLabel(text, self.blocker)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            "color:white; font-size:28px; font-weight:bold;"
        )
        label.setGeometry(0, 0, self.width(), self.height())

        self.blocker.show()

    def hide_blocker(self):
        if hasattr(self, "blocker"):
            self.blocker.deleteLater()

    def load_categories(self):
        first_path = None
        for entry in os.scandir(self.base_dir):
            if entry.is_dir():
                icon = os.path.join(entry.path, "ikona.png")
                if os.path.exists(icon):
                    btn = HoverLabel(entry.name, entry.path, self.display_objects)
                    btn.setPixmap(
                        QPixmap(icon).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
                    self.cat_layout.addWidget(btn)
                    if not first_path:
                        first_path = entry.path
        if first_path:
            self.display_objects(first_path)

    def display_objects(self, cat_path):
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        self.all_items = []
        for i, obj in enumerate(d for d in os.scandir(cat_path) if d.is_dir()):
            widget = ItemWidget(obj.name, obj.path)
            self.all_items.append(widget)
            self.grid.addWidget(widget, i // 6, i % 6)

    def filter_items(self):
        text = self.search_bar.text().lower()
        for item in self.all_items:
            item.setVisible(text in item.name.lower())

# ===================== START =====================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(TOOLTIP_STYLE)
    win = InventoryBrowser()
    win.show()
    sys.exit(app.exec_())
