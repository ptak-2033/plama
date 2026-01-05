import sys
import os
from pathlib import Path

from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow


# === LOKALIZACJA ===
current_file = Path(__file__).resolve()
base_dir = current_file.parents[2]
lista_path = base_dir / "lista.txt"


# === PARSER ===
def _parse_kv_segments(segments):
    """Segments like ['id=1', 'name=abc', 'sygnal=1'] -> dict."""
    out = {}
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        if "=" not in seg:
            # allow bare tokens, ignore
            continue
        k, v = seg.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def parse_lista(path: Path):
    """Nowy format (każda linia = rekord):
    A; id=1; name=...
    B; id=2; name=...; sygnal=1; impuls=on
    """
    anchor_name = "A"
    b_objs = []

    if not path.exists():
        return anchor_name, b_objs

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split(";")]
            side = parts[0].strip() if parts else ""
            kv = _parse_kv_segments(parts[1:])

            if side.upper() == "A":
                anchor_name = kv.get("name", anchor_name)
            elif side.upper() == "B":
                # domyślne wartości (GUI oczekuje sygnal 0..2 i impuls on/off/all)
                if "sygnal" not in kv:
                    kv["sygnal"] = "0"
                if "impuls" not in kv:
                    kv["impuls"] = "on"
                b_objs.append(kv)

    return anchor_name, b_objs


anchor_name, b_objects = parse_lista(lista_path)

class ConnectionsView(QWidget):
    def __init__(self, anchor_name: str, b_objects: list[dict]):
        super().__init__()

        self.anchor_name = anchor_name
        self.b_objects = b_objects
        self.lista_path = lista_path

        self.setMinimumSize(800, 400)

        self.box = 54
        self.spacing = 86

        self.ctrl_mode = [int(o.get("sygnal", 0)) for o in self.b_objects]
        self.ctrl_gate = [o.get("impuls", "on").upper() for o in self.b_objects]
        self.ctrl_rects = []

        self._last_mtime = os.path.getmtime(self.lista_path)
        self.file_timer = QTimer(self)
        self.file_timer.timeout.connect(self.check_file_update)
        self.file_timer.start(300)

        # Kolory
        self.bg = QColor("#0f1115")
        self.line = QColor("#3b414a")
        self.text = QColor("#e8edf2")

        self.a_fill = QColor("#ff9f1a")
        self.a_border = QColor("#ffd29a")

        self.b_fill = QColor("#25c26e")
        self.b_border = QColor("#a9ffd0")

        self.label_muted = QColor("#a9b4bf")

    # === FILE WATCH ===
    def check_file_update(self):
        mtime = os.path.getmtime(self.lista_path)
        if mtime != self._last_mtime:
            self._last_mtime = mtime
            self.reload_from_file()

    def reload_from_file(self):
        new_anchor, new_b = parse_lista(self.lista_path)
        self.anchor_name = new_anchor
        self.b_objects = new_b
        self.ctrl_mode = [int(o.get("sygnal", 0)) for o in new_b]
        self.ctrl_gate = [o.get("impuls", "on").upper() for o in new_b]
        self.update()

    def write_back_to_file(self):
        # Zachowujemy oryginalne linie/układ, podmieniamy tylko sygnal + impuls w liniach 'B; ...'
        with open(self.lista_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        b_index = 0
        for i, raw in enumerate(lines):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split(";")]
            if not parts:
                continue

            side = parts[0].strip().upper()
            if side != "B":
                continue

            kv = _parse_kv_segments(parts[1:])

            # jeśli plik ma więcej B niż GUI, zostawiamy resztę bez zmian
            if b_index >= len(self.ctrl_mode) or b_index >= len(self.ctrl_gate):
                continue

            kv["sygnal"] = str(self.ctrl_mode[b_index])
            kv["impuls"] = self.ctrl_gate[b_index].lower()

            # porządek kluczy: id, name, sygnal, impuls, reszta
            ordered = []
            for k in ["id", "name", "sygnal", "impuls"]:
                if k in kv:
                    ordered.append((k, kv.pop(k)))
            # reszta w stabilnym porządku alfabetycznym
            for k in sorted(kv.keys()):
                ordered.append((k, kv[k]))

            lines[i] = "B; " + "; ".join(f"{k}={v}" for k, v in ordered) + "\n"
            b_index += 1

        with open(self.lista_path, "w", encoding="utf-8") as f:
            f.writelines(lines)


    # === KLIK ===
    def mousePressEvent(self, event):
        pos = event.pos()
        for idx, r1, r2 in self.ctrl_rects:
            if r1.contains(pos):
                self.ctrl_mode[idx] = (self.ctrl_mode[idx] + 1) % 3
                self.write_back_to_file()
                self.update()
                return
            if r2.contains(pos):
                seq = ["ON", "OFF", "ALL"]
                cur = seq.index(self.ctrl_gate[idx])
                self.ctrl_gate[idx] = seq[(cur + 1) % 3]
                self.write_back_to_file()
                self.update()
                return

    # === RYSOWANIE ===
    def paintEvent(self, event):
        self.ctrl_rects.clear()

        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), self.bg)

        box = self.box
        spacing = self.spacing

        A_x, A_y = int(w * 0.22), int(h * 0.5)
        a_center = QPointF(A_x, A_y)

        count = len(self.b_objects)
        start_y = A_y if count <= 1 else A_y - ((count - 1) * spacing) // 2

        b_centers = [
            QPointF(int(w * 0.78), int(start_y + i * spacing))
            for i in range(count)
        ]

        def lerp(p1, p2, t):
            return QPointF(
                p1.x() + (p2.x() - p1.x()) * t,
                p1.y() + (p2.y() - p1.y()) * t
            )

        painter.setPen(QPen(self.line, 2))

        for idx, b in enumerate(b_centers):
            start = QPointF(a_center.x() + box / 2, a_center.y())
            end = QPointF(b.x() - box / 2, b.y())
            painter.drawLine(start, end)

            c1 = lerp(start, end, 0.33)
            c2 = lerp(start, end, 0.66)

            size = 26
            r1 = QRectF(c1.x() - size/2, c1.y() - size/2, size, size)
            r2 = QRectF(c2.x() - size/2, c2.y() - size/2, size, size)
            self.ctrl_rects.append((idx, r1, r2))

            painter.setBrush(QColor("#1f2933"))
            painter.setPen(QPen(QColor("#6b7280"), 2))
            painter.drawRect(r1)
            painter.setPen(QColor("#e5e7eb"))
            painter.drawText(r1, Qt.AlignCenter, str(self.ctrl_mode[idx]))

            painter.setBrush(QColor("#111827"))
            painter.setPen(QPen(QColor("#9ca3af"), 2))
            painter.drawRect(r2)
            painter.setPen(QColor("#22c55e"))
            painter.drawText(r2, Qt.AlignCenter, self.ctrl_gate[idx])

        # === A ===
        a_rect = QRectF(A_x - box/2, A_y - box/2, box, box)
        painter.setPen(QPen(self.a_border, 3))
        painter.setBrush(self.a_fill)
        painter.drawRoundedRect(a_rect, 10, 10)

        painter.setPen(self.text)
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(a_rect, Qt.AlignCenter, "A")

        # NAZWA A NAD
        painter.setFont(QFont("Arial", 11))
        painter.setPen(self.label_muted)
        painter.drawText(
            QRectF(a_rect.left() - 100, a_rect.top() - 28, a_rect.width() + 200, 20),
            Qt.AlignCenter,
            self.anchor_name
        )

        # === B ===
        for i, (b_center, obj) in enumerate(zip(b_centers, self.b_objects)):
            b_rect = QRectF(
                b_center.x() - box/2,
                b_center.y() - box/2,
                box,
                box
            )

            # zielony kwadrat
            painter.setPen(QPen(self.b_border, 3))
            painter.setBrush(self.b_fill)
            painter.drawRoundedRect(b_rect, 10, 10)

            painter.setPen(QColor("#072012"))
            painter.setFont(QFont("Arial", 14, QFont.Bold))
            painter.drawText(b_rect, Qt.AlignCenter, "B")

            # NAZWA NAD B
            painter.setFont(QFont("Arial", 11))
            painter.setPen(self.label_muted)
            painter.drawText(
                QRectF(b_rect.left() - 140, b_rect.top() - 28, b_rect.width() + 280, 20),
                Qt.AlignCenter,
                obj.get("name", f"B{i+1}")
            )

        painter.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PLAMA – połączenia")
        self.setCentralWidget(ConnectionsView(anchor_name, b_objects))
        self.resize(900, 450)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
