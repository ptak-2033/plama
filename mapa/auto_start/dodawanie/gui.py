import sys
import math
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QColor, QPixmap, QFont, QPainterPath
from PyQt5.QtCore import Qt, QRectF, QPoint

# Konfiguracja
BASE_DIR = Path(__file__).resolve().parent
SIZE = 700
CENTER = QPoint(SIZE // 2, SIZE // 2)
OUTER_R = 300
INNER_R = 100
ICON_SIZE = 54

# Kolory
BG_RING = QColor(45, 45, 45, 180)      # Ciemne tło
HOVER_RING = QColor(0, 200, 100, 200)   # Zielony hover
TEXT_COLOR = QColor(255, 255, 255)

class WeaponWheel(QWidget):
    def __init__(self):
        super().__init__()
        self.items = self.load_items()
        self.hover_index = -1  # Przechowujemy indeks najechanego sektora

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.resize(SIZE, SIZE)
        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - SIZE) // 2, (screen.height() - SIZE) // 2)

    def load_items(self):
        items = []
        # Szukamy folderów zawierających ikona.png i gui.py
        for f in sorted(BASE_DIR.iterdir()):
            if f.is_dir():
                icon_path = f / "ikona.png"
                gui_path = f / "gui.py"
                if icon_path.exists() and gui_path.exists():
                    items.append({
                        "name": f.name,
                        "path": f,
                        "icon": QPixmap(str(icon_path)).scaled(
                            ICON_SIZE, ICON_SIZE,
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                    })
        return items

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        n = len(self.items)
        if n == 0:
            return

        angle_step = 360 / n
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))

        for i, item in enumerate(self.items):
            # Obliczanie kąta startowego (odejmujemy 90, aby zacząć od góry)
            start_angle = i * angle_step - 90
            
            # 1. Rysowanie tła sektora
            is_hovered = (i == self.hover_index)
            color = HOVER_RING if is_hovered else BG_RING
            p.setBrush(color)
            p.setPen(Qt.NoPen)

            path = QPainterPath()
            path.arcMoveTo(QRectF(CENTER.x()-OUTER_R, CENTER.y()-OUTER_R, OUTER_R*2, OUTER_R*2), -start_angle)
            path.arcTo(QRectF(CENTER.x()-OUTER_R, CENTER.y()-OUTER_R, OUTER_R*2, OUTER_R*2), -start_angle, -angle_step)
            path.arcTo(QRectF(CENTER.x()-INNER_R, CENTER.y()-INNER_R, INNER_R*2, INNER_R*2), -start_angle - angle_step, angle_step)
            path.closeSubpath()
            p.drawPath(path)

            # 2. Obliczanie pozycji dla ikony i tekstu (środek łuku)
            mid_angle_rad = math.radians(start_angle + angle_step / 2)
            dist_center = (OUTER_R + INNER_R) / 2
            
            x = CENTER.x() + math.cos(mid_angle_rad) * dist_center
            y = CENTER.y() + math.sin(mid_angle_rad) * dist_center

            # Rysowanie ikony
            icon_rect = QRectF(x - ICON_SIZE/2, y - ICON_SIZE/2, ICON_SIZE, ICON_SIZE)
            p.drawPixmap(icon_rect.toRect(), item["icon"])

            # Rysowanie tekstu pod ikoną
            p.setPen(TEXT_COLOR)
            text_rect = QRectF(x - 80, y + (ICON_SIZE/2) + 5, 160, 25)
            p.drawText(text_rect, Qt.AlignCenter, item["name"])

    def get_sector_under_mouse(self, pos):
        dx = pos.x() - CENTER.x()
        dy = pos.y() - CENTER.y()
        distance = math.hypot(dx, dy)

        # Sprawdzenie czy mysz jest w obrębie pierścienia
        if not (INNER_R <= distance <= OUTER_R):
            return -1

        # Obliczanie kąta w stopniach (0-360)
        angle = math.degrees(math.atan2(dy, dx))
        angle = (angle + 90) % 360  # Korekta, aby góra była zerem
        
        n = len(self.items)
        if n == 0: return -1
        
        sector = int(angle // (360 / n))
        return sector if sector < n else n - 1

    def mouseMoveEvent(self, event):
        new_hover = self.get_sector_under_mouse(event.pos())
        if new_hover != self.hover_index:
            self.hover_index = new_hover
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self.get_sector_under_mouse(event.pos())
            if idx != -1:
                item = self.items[idx]
                script_path = item["path"] / "gui.py"
                
                # Uruchomienie skryptu w tle
                subprocess.Popen(
                    [sys.executable, str(script_path)],
                    cwd=str(item["path"])
                )
                self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    wheel = WeaponWheel()
    wheel.show()
    sys.exit(app.exec_())