import sys
import subprocess
from pathlib import Path
# USUNIĘTO: import unicodedata
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
    QCheckBox,
)
from PyQt5.QtGui import QColor, QPalette


class FileSection(QWidget):
    def __init__(self, title, file_path: Path, parent=None):
        super().__init__(parent)

        self.file_path = file_path

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)

        self.label = QLabel(title)
        self.label.setObjectName("sectionLabel")

        self.editor = QTextEdit()
        self.editor.setLineWrapMode(QTextEdit.NoWrap)

        layout.addWidget(self.label)
        layout.addWidget(self.editor)

        self.setLayout(layout)

        # Wczytanie pliku
        self.load_file()

    def load_file(self):
        if self.file_path.exists():
            try:
                text = self.file_path.read_text(encoding="utf-8")
            except Exception:
                text = self.file_path.read_text(errors="replace")
            self.editor.setPlainText(text)

    def get_text(self):
        return self.editor.toPlainText()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.gui_ready = False

        # ============================
        # SYSTEM ŚCIEŻEK (POPRAWNY)
        # ============================

        current_file = Path(__file__).resolve()

        # S i F → obok gui.py
        self.base_dir_local = current_file.parent

        # pamięć GUI obok gui.py
        self.gui_memory_path = self.base_dir_local / "pamieć_gui.txt"

        # Reszta → 2 poziomy wyżej
        self.base_dir_root = current_file.parents[2]

        # GŁÓWNE PLIKI SYSTEMOWE
        self.config_path     = self.base_dir_root / "konfiguracja.txt"
        self.instrukcje_path = self.base_dir_root / "instrukcje.txt"
        self.wejscie_path    = self.base_dir_root / "wejście.txt"
        self.wyjscie_path    = self.base_dir_root / "wyjście.txt"

        # FORMATY FORMUŁ (F)
        self.formula_files = {
            "tożsamość": self.base_dir_local / "f_tożsamość.txt",
            "zadanie":   self.base_dir_local / "f_zadanie.txt",
            "zakazy":    self.base_dir_local / "f_zakazy.txt",
            "przykłady": self.base_dir_local / "f_przykłady.txt",
        }

        # TREŚCI FORMUŁ (S)
        self.content_files = {
            "tożsamość": self.base_dir_local / "s_tożsamość.txt",
            "zadanie":   self.base_dir_local / "s_zadanie.txt",
            "zakazy":    self.base_dir_local / "s_zakazy.txt",
            "przykłady": self.base_dir_local / "s_przykłady.txt",
        }

        # KOLEJNOŚĆ FORMUŁ (ŚWIĘTA)
        self.formula_order = ["tożsamość", "zadanie", "zakazy", "przykłady"]
        
        # =====================================
        # GUI (Dalsza część bez zmian)
        # =====================================
        central = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # -------- GÓRNA BELKA --------
        top = QHBoxLayout()
        self.preview_btn = QPushButton("Podgląd instrukcji")
       
        self.preview_btn.setObjectName("previewButton")
        
        top.addWidget(self.preview_btn)
        top.addStretch()
        main_layout.addLayout(top)

        # -------- BODY --------
        body = QHBoxLayout()

        # LEWA
        left = QVBoxLayout()

        # checkboksy (w tej samej kolejności co formula_order)
        cb_row = QHBoxLayout()
        self.formula_checkboxes = {}
        for name in self.formula_order:
            cb = QCheckBox(name)
            cb.stateChanged.connect(self.on_formula_option_changed)
            self.formula_checkboxes[name] = cb
            cb_row.addWidget(cb)
        cb_row.addStretch()
        left.addLayout(cb_row)
        self._load_gui_memory()

        # kontener formuł / szablonów
        self.formula_container = QWidget()
        self.formula_layout = QHBoxLayout()
        self.formula_layout.setContentsMargins(0, 0, 0, 0)
        self.formula_layout.setSpacing(6)
        self.formula_container.setLayout(self.formula_layout)
        left.addWidget(self.formula_container, stretch=4)

        # wejście / wyjście
        io = QHBoxLayout()
        self.wejscie_section = FileSection("wejście", self.wejscie_path)
        self.wyjscie_section = FileSection("wyjście", self.wyjscie_path)
        io.addWidget(self.wejscie_section)
        io.addWidget(self.wyjscie_section)
        left.addLayout(io, stretch=2)

        # przycisk zapisu
        self.apply_all_btn = QPushButton("ZASTOSUJ WSZYSTKO")
        self.apply_all_btn.setObjectName("applyAllButton")
        left.addWidget(self.apply_all_btn)

        body.addLayout(left, stretch=4)

        # PRAWA – konfiguracja
        right = QVBoxLayout()
        self.config_section = FileSection("konfiguracja", self.config_path)
        right.addWidget(self.config_section)
        body.addLayout(right, stretch=1)

        main_layout.addLayout(body)
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # =====================================
        # OVERLAY "ZAPISANO"
        # =====================================
        self.saved_label = QLabel("ZAPISANO")
        self.saved_label.setVisible(False)
        self.saved_label.setAlignment(Qt.AlignCenter)
        self.saved_label.setParent(self)
        self.saved_label.setStyleSheet("""
            background-color: rgba(0,0,0,180);
            color: #00ff99;
            font-size: 22px;
            font-weight: bold;
            border-radius: 14px;
            padding: 12px 18px;
        """)

        # =====================================
        # PANEL PODGLĄDU
        # =====================================
        self.preview_overlay = QWidget(self)
        self.preview_overlay.setVisible(False)

        pal = self.preview_overlay.palette()
        pal.setColor(QPalette.Window, QColor(0, 0, 0, 170))
        self.preview_overlay.setAutoFillBackground(True)
        self.preview_overlay.setPalette(pal)

        # panel
        self.preview_panel = QWidget(self.preview_overlay)
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(18, 18, 18, 18)
        panel_layout.setSpacing(10)

        title = QLabel("Instrukcje – pełny podgląd (instrukcje.txt)")
        title.setObjectName("sectionLabel")
        panel_layout.addWidget(title)

        self.preview_editor = QTextEdit()
        self.preview_editor.setLineWrapMode(QTextEdit.NoWrap)
        panel_layout.addWidget(self.preview_editor)

        row = QHBoxLayout()
        self.preview_apply_btn = QPushButton("ZASTOSUJ (zapisz)")
        self.preview_close_btn = QPushButton("Zamknij podgląd")
        self.preview_apply_btn.setObjectName("applyAllButton")
        self.preview_close_btn.setObjectName("stopButton")
        row.addWidget(self.preview_apply_btn)
        row.addWidget(self.preview_close_btn)
        row.addStretch()
        panel_layout.addLayout(row)

        self.preview_panel.setLayout(panel_layout)
        self.preview_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(10,18,26,240);
                border-radius: 18px;
                border: 2px solid rgba(0,255,160,130);
            }
        """)

        # aktywne edytory formuł
        self.active_formula_editors = {}

        # zastosuj motyw
        self._apply_theme()

        # watcher
        self.watcher = QFileSystemWatcher(self)
        self._setup_watcher()
        self.watcher.fileChanged.connect(self.on_file_changed)

        # sygnały
        self.apply_all_btn.clicked.connect(self.apply_all)
        self.preview_btn.clicked.connect(self.open_preview)
        self.preview_apply_btn.clicked.connect(self.save_from_preview)
        self.preview_close_btn.clicked.connect(self.close_preview)

        self._rebuild_formula_editors()
        self.gui_ready = True

        self.resize(1500, 900)
        self.setWindowOpacity(0.94)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

    # ========================= STYL =========================

    def _apply_theme(self):
        self.setStyleSheet("""
        QMainWindow {
            background-color: rgba(5, 10, 16, 230);
        }
        QWidget {
            color: #e8f5e9;
            font-family: Segoe UI;
            font-size: 11pt;
        }
        QTextEdit {
            background-color: rgba(10,18,26,230);
            border: 1px solid rgba(0,255,128,120);
            border-radius: 10px;
            padding: 6px;
        }
        QLabel#sectionLabel {
            font-weight: 600;
            color: #c8ffdf;
        }
        QPushButton {
            padding: 6px 18px;
            border-radius: 14px;
            font-weight: 600;
            border: 2px solid rgba(0, 200, 120, 180);
            background-color: #009f4d;
            color: #f1fff8;
        }
        QPushButton:hover {
            background-color: #00b75b;
            border-color: #00ff99;
        }
        QPushButton#stopButton {
            background-color: #c62828;
            border-color: #ff8a65;
            color: #fff4f4;
        }
        QPushButton#stopButton:hover {
            background-color: #e53935;
            border-color: #ffab91;
        }
        QPushButton#applyAllButton {
            background-color: #f9a825;
            border-color: #ffc93c;
            color: #212121;
            font-weight: bold;
            font-size: 12pt;
            padding: 10px 24px;
            border-radius: 16px;
        }
        QPushButton#applyAllButton:hover {
            background-color: #ffca28;
            border-color: #ffe082;
        }
        QPushButton#previewButton {
            background-color: #00897b;
            border-color: #4db6ac;
        }
        QPushButton#previewButton:hover {
            background-color: #00a89a;
            border-color: #80cbc4;
        }
        """)

    # ========================= ROZMIAR / ROZMIESZCZENIE =========================

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # "ZAPISANO" w centrum
        self.saved_label.adjustSize()
        self.saved_label.move(
            (self.width() - self.saved_label.width()) // 2,
            (self.height() - self.saved_label.height()) // 2,
        )

        # overlay pełnoekranowy
        self.preview_overlay.resize(self.size())

        # panel w środku
        w = min(self.width() - 200, 1000)
        h = min(self.height() - 200, 700)
        if w < 600:
            w = self.width() - 80
        if h < 400:
            h = self.height() - 80

        self.preview_panel.resize(w, h)
        self.preview_panel.move(
            (self.width() - w) // 2,
            (self.height() - h) // 2,
        )

    def closeEvent(self, event):
        """Zapis stanu GUI przy zamknięciu okna."""
        self._save_gui_memory()
        super().closeEvent(event)

    def moveEvent(self, event):
        """Zapis stanu GUI przy przesuwaniu okna."""
        if self.gui_ready:
            self._save_gui_memory()
        super().moveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        # "ZAPISANO" w centrum
        self.saved_label.adjustSize()
        self.saved_label.move(
            (self.width() - self.saved_label.width()) // 2,
            (self.height() - self.saved_label.height()) // 2,
        )

        # overlay pełnoekranowy
        self.preview_overlay.resize(self.size())

        # panel w środku
        w = min(self.width() - 200, 1000)
        h = min(self.height() - 200, 700)
        if w < 600:
            w = self.width() - 80
        if h < 400:
            h = self.height() - 80

        self.preview_panel.resize(w, h)
        self.preview_panel.move(
            (self.width() - w) // 2,
            (self.height() - h) // 2,
        )

        # 🔥 auto-zapis rozmiaru okna
        if self.gui_ready:
            self._save_gui_memory()

    def on_formula_option_changed(self, _):
        """Auto-przebudowa + zapamiętywanie stanu checkboksów."""
        if not self.gui_ready:
            return

        self._rebuild_formula_editors()

        # 🔥 auto-zapis zmian checkboxów
        self._save_gui_memory()

    # ========================= WATCHER =========================

    def _setup_watcher(self):
        self.watcher.removePaths(self.watcher.files())
        for p in [self.config_path, self.wejscie_path, self.wyjscie_path]:
            p.touch(exist_ok=True)
            self.watcher.addPath(str(p))

    def on_file_changed(self, path):
        p = Path(path)
        if p == self.config_path:
            self.config_section.load_file()
        elif p == self.wejscie_path:
            self.wejscie_section.load_file()
        elif p == self.wyjscie_path:
            self.wyjscie_section.load_file()

    # ========================= FORMUŁY / SZABLONY =========================

    def _make_formula_box(self, label_name, key):
        """Tworzy pojedynczą kolumnę z etykietą + edytorem."""
        box = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        lab = QLabel(label_name)
        lab.setObjectName("sectionLabel")
        edit = QTextEdit()
        edit.setLineWrapMode(QTextEdit.NoWrap)

        if key != "raw":
            # Wczytujemy czystą treść (bez tagów)
            cp = self.content_files.get(key)
            if cp and cp.exists():
                txt = cp.read_text(encoding="utf-8", errors="replace")
                start_tag = f"<początek_{key}>"
                end_tag = f"<koniec_{key}>"
                start_idx = txt.find(start_tag)
                end_idx = txt.find(end_tag)
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    inner = txt[start_idx + len(start_tag):end_idx].strip()
                    edit.setPlainText(inner)

        layout.addWidget(lab)
        layout.addWidget(edit)
        box.setLayout(layout)

        self.active_formula_editors[key] = edit
        return box
    
    def _load_gui_memory(self):
        """Wczytuje stan GUI z pamieć_gui.txt obok gui.py."""
        if not self.gui_memory_path.exists():
            return

        try:
            txt = self.gui_memory_path.read_text(encoding="utf-8")
            lines = {l.split("=")[0]: l.split("=")[1] for l in txt.splitlines() if "=" in l}
        except:
            return

        # checkboksy
        for key, cb in self.formula_checkboxes.items():
            val = lines.get(f"cb_{key}")
            if val is not None:
                cb.setChecked(val == "1")

        # okno
        x = lines.get("win_x")
        y = lines.get("win_y")
        w = lines.get("win_w")
        h = lines.get("win_h")
        if all([x, y, w, h]):
            try:
                self.move(int(x), int(y))
                self.resize(int(w), int(h))
            except:
                pass

    def _save_gui_memory(self):
        """Zapisuje stan GUI do pamieć_gui.txt obok gui.py."""
        lines = []

        # checkboksy
        for key, cb in self.formula_checkboxes.items():
            lines.append(f"cb_{key}={'1' if cb.isChecked() else '0'}")

        # okno
        lines.append(f"win_x={self.x()}")
        lines.append(f"win_y={self.y()}")
        lines.append(f"win_w={self.width()}")
        lines.append(f"win_h={self.height()}")

        txt = "\n".join(lines)
        self.gui_memory_path.write_text(txt, encoding="utf-8")

    def _rebuild_formula_editors(self):
        """Przebudowuje układ okien formuł (0–4 aktywnych)."""
        while self.formula_layout.count():
            item = self.formula_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.active_formula_editors.clear()

        active = [f for f in self.formula_order if self.formula_checkboxes[f].isChecked()]

        if not active:
            box = self._make_formula_box("surowa instrukcja", "raw")
            self.formula_layout.addWidget(box)
        else:
            for f in active:
                box = self._make_formula_box(f, f)
                self.formula_layout.addWidget(box)

    def _save_tagged_content(self, path: Path, key: str, inner: str):
        """Zapisuje treść w formacie z tagami."""
        start_tag = f"<początek_{key}>"
        end_tag = f"<koniec_{key}>"
        txt = f"{start_tag}\n{inner}\n{end_tag}"
        path.write_text(txt, encoding="utf-8")

    def on_formula_option_changed(self, _):
        """Auto-zapis tekstu i stanu GUI przy zmianie aktywnych formuł."""
        if not self.gui_ready:
            return

        # 1️⃣ Zapisujemy tekst z obecnych edytorów zanim GUI je przebuduje
        active = [f for f in self.formula_order if self.formula_checkboxes[f].isChecked()]
        if active:
            for f in active:
                editor = self.active_formula_editors.get(f)
                if editor:
                    inner = editor.toPlainText()
                    cp = self.content_files.get(f)
                    if cp:
                        self._save_tagged_content(cp, f, inner)
        else:
            # tryb RAW
            raw_editor = self.active_formula_editors.get("raw")
            if raw_editor:
                raw_text = raw_editor.toPlainText()
                self.instrukcje_path.write_text(raw_text, encoding="utf-8")

        # 2️⃣ Przebudowa edytorów po zapisie
        self._rebuild_formula_editors()

        # 3️⃣ Auto-zapis stanu checkboxów i okna
        self._save_gui_memory()

    # ========================= ZAPIS =========================

    def apply_all(self):
        try:
            self.config_path.write_text(self.config_section.get_text(), encoding="utf-8")
            self.wejscie_path.write_text(self.wejscie_section.get_text(), encoding="utf-8")
            self.wyjscie_path.write_text(self.wyjscie_section.get_text(), encoding="utf-8")

            active = [f for f in self.formula_order if self.formula_checkboxes[f].isChecked()]

            # === TRYB RAW ===
            if not active:
                raw = self.active_formula_editors["raw"].toPlainText()
                self.instrukcje_path.write_text(raw, encoding="utf-8")
                self._show_saved()
                return

            parts = []

            # 1. SYNCHRONIZACJA: Zapisujemy treść z edytorów GUI do plików s_ (z tagami)
            for f in active:
                editor = self.active_formula_editors.get(f)
                if editor:
                    inner = editor.toPlainText()
                    cp = self.content_files.get(f)
                    if cp:
                        self._save_tagged_content(cp, f, inner) 

            # 2. BUDOWA INSTRUKCJE.TXT
            # Najpierw wszystkie formaty f_
            for f in active:
                fp = self.formula_files.get(f)
                if fp and fp.exists():
                    txt = fp.read_text(encoding="utf-8", errors="replace")
                    if txt.strip():
                        parts.append(txt.strip())

            # Potem wszystkie szablony s_ (z tagami)
            for f in active:
                cp = self.content_files.get(f)
                if cp and cp.exists():
                    txt = cp.read_text(encoding="utf-8", errors="replace")
                    if txt.strip():
                        parts.append(txt.strip())

            # Zapis
            full = "\n\n".join(parts)
            self.instrukcje_path.write_text(full, encoding="utf-8")

            self._show_saved()
            self._save_gui_memory()

        except Exception as e:
            print("Błąd zapisu:", e)

    def _show_saved(self):
        self.saved_label.setVisible(True)
        QTimer.singleShot(1000, lambda: self.saved_label.setVisible(False))

    # ========================= PODGLĄD INSTRUKCJI =========================

    def open_preview(self):
        """Otwiera panel z pełnym podglądem instrukcji."""
        if self.instrukcje_path.exists():
            try:
                txt = self.instrukcje_path.read_text(encoding="utf-8")
            except Exception:
                txt = self.instrukcje_path.read_text(errors="replace")
            self.preview_editor.setPlainText(txt)
        else:
            self.preview_editor.clear()

        self.preview_overlay.raise_()
        self.preview_overlay.setVisible(True)

    def save_from_preview(self):
        """Zapisuje instrukcje bezpośrednio z panelu podglądu."""
        txt = self.preview_editor.toPlainText()
        self.instrukcje_path.write_text(txt, encoding="utf-8")
        self.preview_overlay.setVisible(False)

    def close_preview(self):
        """Zamyka panel podglądu (bez zapisu)."""
        self.preview_overlay.setVisible(False)

# ========================= ENTRYPOINT =========================

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()