#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLAMA – GUI SERWERA LLM
Wizualnie inspirowane starym gui promptów, ale logika pod serwer:
- edycja konfiguracje.txt (host, port, model, parametry)
- start / stop / restart serwera (start.py + stop_serwer)
- status na podstawie mapa_dane.txt (proces=on/off/error)
- podgląd logów z log.txt w overlayu
"""

import sys
import os
import subprocess
from pathlib import Path

from PyQt5.QtCore import Qt, QFileSystemWatcher, QTimer
from PyQt5.QtGui import QColor, QPalette
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
    QLineEdit,
    QSpinBox,
    QComboBox,
    QGroupBox,
    QMessageBox,
)

# ===================== POMOCNICZE =====================

def read_kv_config(path: Path) -> dict:
    """Czyta prosty config key=value (tak jak w start.py)."""
    cfg = {}
    if not path.exists():
        return cfg
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = [x.strip() for x in line.split("=", 1)]
        k = k.lower().replace("-", "_")
        vraw = v.strip().strip('"').strip("'")
        if vraw.lower() in ("true", "false"):
            v = vraw.lower() == "true"
        else:
            try:
                v = int(vraw)
            except ValueError:
                v = vraw
        cfg[k] = v
    return cfg


def write_kv_config(path: Path, data: dict):
    """Zapisuje key=value w prostym formacie."""
    lines = [
        "# konfiguracje serwera PLAMA",
        "# edytowane z poziomu gui.py (serwer/opcje/edytuj)",
        "",
    ]
    order = [
        "model",
        "host",
        "port",
        "c",
        "n_gpu_layers",
        "threads",
        "prio",
        "prio_batch",
        "mlock",
        "offline",
    ]
    for k in order:
        if k in data:
            v = data[k]
            if isinstance(v, bool):
                v = "true" if v else "false"
            lines.append(f"{k} = {v}")
    # dorzuć resztę ewentualnych kluczy
    for k, v in data.items():
        if k in order:
            continue
        if isinstance(v, bool):
            v = "true" if v else "false"
        lines.append(f"{k} = {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_models(root: Path):
    """Skanuje .gguf w silnik/ i modele/ (relatywne ścieżki)."""
    candidates = []
    for sub in ("silnik", "modele"):
        base = root / sub
        if base.exists() and base.is_dir():
            for p in base.rglob("*.gguf"):
                try:
                    rel = p.relative_to(root)
                except ValueError:
                    rel = p.name
                candidates.append(str(rel).replace("\\", "/"))
    candidates = sorted(set(candidates))
    return candidates


def read_proces_state(mapa_path: Path) -> str:
    """Czyta proces=on/off/error z mapa_dane.txt."""
    if not mapa_path.exists():
        return "unknown"
    for line in mapa_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        l = line.strip().lower()
        if l.startswith("proces="):
            return l.split("=", 1)[1].strip()
    return "unknown"


# ===================== GŁÓWNE OKNO =====================

class ServerGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # ŚCIEŻKI
        current_file = Path(__file__).resolve()

        # root obiektu serwer: .../serwer
        self.root_dir = current_file.parents[2]

        self.config_path = self.root_dir / "konfiguracje.txt"
        self.mapa_path = self.root_dir / "mapa_dane.txt"
        self.log_path = self.root_dir / "log.txt"
        self.start_script = self.root_dir / "start.py"
        self.stop_script = self.root_dir / "stop_serwer"
        self.gotowe_path = self.root_dir / "gotowe.txt"

        # pamięć GUI (pozycja/rozmiar)
        self.gui_state_path = current_file.parent / "pamiec_gui_serwer.txt"

        # STAN
        self.cfg = {}
        self.models = []
        self.gui_ready = False

        # UI
        self._build_ui()
        self._apply_theme()

        # watcher
        self.watcher = QFileSystemWatcher(self)
        self._setup_watcher()
        self.watcher.fileChanged.connect(self.on_file_changed)

        # dane startowe
        self.load_config_to_widgets()
        self.refresh_status_label()
        self.refresh_config_view()
        self.load_gui_state()

        self.gui_ready = True

    # ---------- UI BUDOWA ----------

    def _build_ui(self):
        self.setWindowTitle("PLAMA – Serwer LLM")

        central = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # TOP BAR
        top = QHBoxLayout()

        self.status_label = QLabel("STATUS: ?")
        self.status_label.setObjectName("statusLabel")

        self.start_btn = QPushButton("URUCHOM SERWER")
        self.start_btn.setObjectName("startButton")

        self.stop_btn = QPushButton("ZATRZYMAJ")
        self.stop_btn.setObjectName("stopButton")

        self.restart_btn = QPushButton("RESTART")
        self.restart_btn.setObjectName("restartButton")

        self.logs_btn = QPushButton("LOGI")
        self.logs_btn.setObjectName("previewButton")

        top.addWidget(self.status_label)
        top.addStretch()
        top.addWidget(self.start_btn)
        top.addWidget(self.stop_btn)
        top.addWidget(self.restart_btn)
        top.addWidget(self.logs_btn)
        main_layout.addLayout(top)

        # BODY
        body = QHBoxLayout()

        # LEWA STRONA – formularz
        left = QVBoxLayout()

        # --- Połączenie ---
        conn_group = QGroupBox("Połączenie")
        conn_layout = QVBoxLayout()

        row_host = QHBoxLayout()
        row_host.addWidget(QLabel("Host:"))
        self.host_edit = QLineEdit()
        row_host.addWidget(self.host_edit)
        conn_layout.addLayout(row_host)

        row_port = QHBoxLayout()
        row_port.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        row_port.addWidget(self.port_spin)
        conn_layout.addLayout(row_port)

        conn_group.setLayout(conn_layout)
        left.addWidget(conn_group)

        # --- Model ---
        model_group = QGroupBox("Model (.gguf)")
        model_layout = QVBoxLayout()

        row_model = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(False)
        row_model.addWidget(self.model_combo)
        self.refresh_models_btn = QPushButton("Odśwież modele")
        row_model.addWidget(self.refresh_models_btn)
        model_layout.addLayout(row_model)

        model_group.setLayout(model_layout)
        left.addWidget(model_group)

        # --- Parametry ---
        params_group = QGroupBox("Parametry serwera")
        params_layout = QVBoxLayout()

        # context
        row_c = QHBoxLayout()
        row_c.addWidget(QLabel("Kontekst (c):"))
        self.c_spin = QSpinBox()
        self.c_spin.setRange(512, 32768)
        self.c_spin.setSingleStep(512)
        row_c.addWidget(self.c_spin)
        params_layout.addLayout(row_c)

        # n_gpu_layers
        row_ngl = QHBoxLayout()
        row_ngl.addWidget(QLabel("n_gpu_layers:"))
        self.ngl_spin = QSpinBox()
        self.ngl_spin.setRange(0, 200)
        row_ngl.addWidget(self.ngl_spin)
        params_layout.addLayout(row_ngl)

        # threads
        row_threads = QHBoxLayout()
        row_threads.addWidget(QLabel("threads:"))
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, os.cpu_count() or 64)
        row_threads.addWidget(self.threads_spin)
        params_layout.addLayout(row_threads)

        # prio
        row_prio = QHBoxLayout()
        row_prio.addWidget(QLabel("prio:"))
        self.prio_spin = QSpinBox()
        self.prio_spin.setRange(-10, 10)
        row_prio.addWidget(self.prio_spin)
        params_layout.addLayout(row_prio)

        # prio_batch
        row_prio_b = QHBoxLayout()
        row_prio_b.addWidget(QLabel("prio_batch:"))
        self.prio_batch_spin = QSpinBox()
        self.prio_batch_spin.setRange(-10, 10)
        row_prio_b.addWidget(self.prio_batch_spin)
        params_layout.addLayout(row_prio_b)

        # flagi
        flags_row = QHBoxLayout()
        self.mlock_cb = QCheckBox("mlock")
        self.offline_cb = QCheckBox("offline")
        flags_row.addWidget(self.mlock_cb)
        flags_row.addWidget(self.offline_cb)
        flags_row.addStretch()
        params_layout.addLayout(flags_row)

        params_group.setLayout(params_layout)
        left.addWidget(params_group)

        # przyciski konfiguracji
        conf_btn_row = QHBoxLayout()
        self.save_cfg_btn = QPushButton("ZAPISZ KONFIGURACJĘ")
        self.save_cfg_btn.setObjectName("applyAllButton")
        self.open_cfg_btn = QPushButton("Otwórz konfiguracje.txt")
        self.open_cfg_btn.setObjectName("previewButton")
        conf_btn_row.addWidget(self.save_cfg_btn)
        conf_btn_row.addWidget(self.open_cfg_btn)
        left.addLayout(conf_btn_row)

        left.addStretch()
        body.addLayout(left, stretch=3)

        # PRAWA STRONA – podgląd konfiguracji
        right = QVBoxLayout()
        self.cfg_view_label = QLabel("Podgląd konfiguracje.txt")
        self.cfg_view_label.setObjectName("sectionLabel")
        self.cfg_view = QTextEdit()
        self.cfg_view.setReadOnly(True)
        right.addWidget(self.cfg_view_label)
        right.addWidget(self.cfg_view)
        body.addLayout(right, stretch=2)

        main_layout.addLayout(body)

        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # overlay "ZAPISANO"
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

        # overlay z logami
        self.logs_overlay = QWidget(self)
        self.logs_overlay.setVisible(False)
        pal = self.logs_overlay.palette()
        pal.setColor(QPalette.Window, QColor(0, 0, 0, 170))
        self.logs_overlay.setAutoFillBackground(True)
        self.logs_overlay.setPalette(pal)

        self.logs_panel = QWidget(self.logs_overlay)
        lp_layout = QVBoxLayout()
        lp_layout.setContentsMargins(18, 18, 18, 18)
        lp_layout.setSpacing(10)

        logs_title = QLabel("Logi serwera (log.txt)")
        logs_title.setObjectName("sectionLabel")
        lp_layout.addWidget(logs_title)

        self.logs_editor = QTextEdit()
        self.logs_editor.setLineWrapMode(QTextEdit.NoWrap)
        lp_layout.addWidget(self.logs_editor)

        logs_btn_row = QHBoxLayout()
        self.logs_refresh_btn = QPushButton("Odśwież")
        self.logs_close_btn = QPushButton("Zamknij")
        self.logs_refresh_btn.setObjectName("previewButton")
        self.logs_close_btn.setObjectName("stopButton")
        logs_btn_row.addWidget(self.logs_refresh_btn)
        logs_btn_row.addWidget(self.logs_close_btn)
        logs_btn_row.addStretch()
        lp_layout.addLayout(logs_btn_row)

        self.logs_panel.setLayout(lp_layout)
        self.logs_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(10,18,26,240);
                border-radius: 18px;
                border: 2px solid rgba(0,255,160,130);
            }
        """)

        # SYGNAŁY
        self.start_btn.clicked.connect(self.on_start_clicked)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        self.restart_btn.clicked.connect(self.on_restart_clicked)
        self.logs_btn.clicked.connect(self.open_logs_overlay)
        self.logs_refresh_btn.clicked.connect(self.load_logs)
        self.logs_close_btn.clicked.connect(self.close_logs_overlay)
        self.save_cfg_btn.clicked.connect(self.on_save_config_clicked)
        self.open_cfg_btn.clicked.connect(self.open_config_external)
        self.refresh_models_btn.clicked.connect(self.populate_models_combo)

        # rozmiar/okno
        self.resize(1400, 800)
        self.setWindowOpacity(0.95)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

    # ---------- STYL ----------

    def _apply_theme(self):
        self.setStyleSheet("""
        QMainWindow {
            background-color: rgba(5, 10, 16, 230);
        }
        QWidget {
            color: #e8f5e9;
            font-family: Segoe UI;
            font-size: 10pt;
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
        QLabel#statusLabel {
            font-weight: 700;
            font-size: 12pt;
        }
        QPushButton {
            padding: 6px 16px;
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
        QPushButton#startButton {
            background-color: #00a152;
            border-color: #69f0ae;
        }
        QPushButton#restartButton {
            background-color: #f9a825;
            border-color: #ffc93c;
            color: #212121;
        }
        QPushButton#restartButton:hover {
            background-color: #ffca28;
            border-color: #ffe082;
        }
        QPushButton#applyAllButton {
            background-color: #f9a825;
            border-color: #ffc93c;
            color: #212121;
            font-weight: bold;
            font-size: 11pt;
            padding: 8px 22px;
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
        QGroupBox {
            border: 1px solid rgba(0,255,128,100);
            border-radius: 10px;
            margin-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px 0 4px;
            color: #a5d6a7;
        }
                           
                QLineEdit, QSpinBox, QComboBox {
            background-color: rgba(10,18,26,230);
            color: #e8f5e9;
            border: 1px solid rgba(0,255,128,120);
            border-radius: 8px;
            padding: 4px 6px;
        }

        QSpinBox::up-button, QSpinBox::down-button {
            background-color: rgba(20,30,38,180);
            border: 1px solid rgba(0,255,128,80);
            width: 14px;
        }

        QComboBox QAbstractItemView {
            background-color: rgba(10,18,26,230);
            color: #e8f5e9;
            selection-background-color: #00b75b;
        }

        """)
            
    # ---------- LAYOUT / ZDARZENIA OKNA ----------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # "ZAPISANO" w centrum
        self.saved_label.adjustSize()
        self.saved_label.move(
            (self.width() - self.saved_label.width()) // 2,
            (self.height() - self.saved_label.height()) // 2,
        )
        # overlay logów
        self.logs_overlay.resize(self.size())
        w = min(self.width() - 200, 1000)
        h = min(self.height() - 200, 700)
        if w < 600:
            w = self.width() - 80
        if h < 400:
            h = self.height() - 80
        self.logs_panel.resize(w, h)
        self.logs_panel.move(
            (self.width() - w) // 2,
            (self.height() - h) // 2,
        )
        if self.gui_ready:
            self.save_gui_state()

    def moveEvent(self, event):
        super().moveEvent(event)
        if self.gui_ready:
            self.save_gui_state()

    def closeEvent(self, event):
        if self.gui_ready:
            self.save_gui_state()
        super().closeEvent(event)

    # ---------- WATCHER ----------

    def _setup_watcher(self):
        self.watcher.removePaths(self.watcher.files())
        for p in [self.mapa_path, self.log_path, self.config_path]:
            p.touch(exist_ok=True)
            self.watcher.addPath(str(p))

    def on_file_changed(self, path):
        p = Path(path)
        if p == self.mapa_path:
            self.refresh_status_label()
        elif p == self.log_path:
            # jak overlay jest otwarty – odśwież logi
            if self.logs_overlay.isVisible():
                self.load_logs()
        elif p == self.config_path:
            self.refresh_config_view()
            # nie nadpisuj widgetów jeśli user coś wpisuje ręcznie

    # ---------- STAN GUI ----------

    def load_gui_state(self):
        if not self.gui_state_path.exists():
            return
        try:
            lines = {
                l.split("=", 1)[0]: l.split("=", 1)[1]
                for l in self.gui_state_path.read_text(encoding="utf-8").splitlines()
                if "=" in l
            }
            x = int(lines.get("x", "100"))
            y = int(lines.get("y", "100"))
            w = int(lines.get("w", "1400"))
            h = int(lines.get("h", "800"))
            self.setGeometry(x, y, w, h)
        except Exception:
            pass

    def save_gui_state(self):
        try:
            txt = "\n".join([
                f"x={self.x()}",
                f"y={self.y()}",
                f"w={self.width()}",
                f"h={self.height()}",
            ])
            self.gui_state_path.write_text(txt, encoding="utf-8")
        except Exception:
            pass

    # ---------- KONFIGURACJA ----------

    def load_config_to_widgets(self):
        # wczytaj config
        self.cfg = read_kv_config(self.config_path)

        # host/port
        self.host_edit.setText(str(self.cfg.get("host", "127.0.0.1")))
        self.port_spin.setValue(int(self.cfg.get("port", 3333)))

        # modele
        self.populate_models_combo()
        model_val = str(self.cfg.get("model", "silnik/Llama-PLLuM-8B-base.Q5_K_M.gguf"))
        idx = self.model_combo.findText(model_val)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        elif self.model_combo.count() > 0:
            self.model_combo.setCurrentIndex(0)

        # parametry
        self.c_spin.setValue(int(self.cfg.get("c", 8192)))
        self.ngl_spin.setValue(int(self.cfg.get("n_gpu_layers", self.cfg.get("ngl", 99))))
        self.threads_spin.setValue(int(self.cfg.get("threads", max(1, os.cpu_count() or 8))))
        self.prio_spin.setValue(int(self.cfg.get("prio", 0)))
        self.prio_batch_spin.setValue(int(self.cfg.get("prio_batch", 0)))
        self.mlock_cb.setChecked(bool(self.cfg.get("mlock", False)))
        self.offline_cb.setChecked(bool(self.cfg.get("offline", False)))

    def populate_models_combo(self):
        self.models = find_models(self.root_dir)
        self.model_combo.clear()
        if not self.models:
            self.model_combo.addItem("brak znalezionych modeli (.gguf)")
            self.model_combo.setEnabled(False)
        else:
            self.model_combo.setEnabled(True)
            for m in self.models:
                self.model_combo.addItem(m)

    def collect_widgets_to_config(self):
        cfg = dict(self.cfg)  # kopia
        cfg["host"] = self.host_edit.text().strip() or "127.0.0.1"
        cfg["port"] = int(self.port_spin.value())
        if self.model_combo.isEnabled() and self.model_combo.currentText():
            cfg["model"] = self.model_combo.currentText().strip()
        cfg["c"] = int(self.c_spin.value())
        cfg["n_gpu_layers"] = int(self.ngl_spin.value())
        cfg["threads"] = int(self.threads_spin.value())
        cfg["prio"] = int(self.prio_spin.value())
        cfg["prio_batch"] = int(self.prio_batch_spin.value())
        cfg["mlock"] = bool(self.mlock_cb.isChecked())
        cfg["offline"] = bool(self.offline_cb.isChecked())
        return cfg

    def refresh_config_view(self):
        try:
            txt = self.config_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            txt = ""
        self.cfg_view.setPlainText(txt)

    def on_save_config_clicked(self):
        try:
            cfg = self.collect_widgets_to_config()
            write_kv_config(self.config_path, cfg)
            self.cfg = cfg
            self.refresh_config_view()
            self.show_saved_overlay()
        except Exception as e:
            QMessageBox.critical(self, "Błąd zapisu", f"Nie udało się zapisać konfiguracji:\n{e}")

    def open_config_external(self):
        # otwórz w domyślnym edytorze
        if not self.config_path.exists():
            self.config_path.touch()
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(self.config_path))  # type: ignore
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.config_path)])
            else:
                subprocess.Popen(["xdg-open", str(self.config_path)])
        except Exception as e:
            QMessageBox.warning(self, "Info", f"Nie udało się otworzyć pliku:\n{e}")

    # ---------- STATUS ----------

    def refresh_status_label(self):
        state = read_proces_state(self.mapa_path)
        text = state.upper()
        color = "#cccccc"
        if state == "on":
            color = "#00e676"
            text = "ON"
        elif state == "off":
            color = "#ffca28"
            text = "OFF"
        elif state == "error":
            color = "#ff5252"
            text = "ERROR"
        self.status_label.setText(f"STATUS: <span style='color:{color};'>{text}</span>")

    # ---------- START / STOP / RESTART ----------

    def on_start_clicked(self):
        # nie spamuj kilku instancji
        current_state = read_proces_state(self.mapa_path)
        if current_state == "on":
            res = QMessageBox.question(
                self,
                "Serwer już działa",
                "proces=on – uruchomić mimo to (druga instancja)?",
            )
            if res != QMessageBox.Yes:
                return

        if not self.start_script.exists():
            QMessageBox.critical(self, "Błąd", f"Brak start.py w {self.root_dir}")
            return

        # zapis aktualnej konfiguracji przed startem
        self.on_save_config_clicked()

        try:
            cmd = [sys.executable, str(self.start_script)]
            creationflags = 0
            if os.name == "nt":
                creationflags = 0x08000000  # ukryte okno
            subprocess.Popen(
                cmd,
                cwd=str(self.root_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            self.refresh_status_label()
        except Exception as e:
            QMessageBox.critical(self, "Błąd uruchamiania", f"Nie udało się uruchomić serwera:\n{e}")

    def on_stop_clicked(self):
        if not self.stop_script.exists():
            QMessageBox.warning(
                self,
                "Brak stop_serwer",
                "Nie znaleziono pliku stop_serwer – zatrzymanie może wymagać ręcznej ingerencji."
            )
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen([str(self.stop_script)], cwd=str(self.root_dir), shell=True)
            else:
                subprocess.Popen([str(self.stop_script)], cwd=str(self.root_dir))
        except Exception as e:
            QMessageBox.critical(self, "Błąd zatrzymania", f"Nie udało się wywołać stop_serwer:\n{e}")

    def on_restart_clicked(self):
        self.on_stop_clicked()
        # mała pauza zanim odpalimy ponownie
        QTimer.singleShot(1500, self.on_start_clicked)

    # ---------- LOGI ----------

    def open_logs_overlay(self):
        self.load_logs()
        self.logs_overlay.raise_()
        self.logs_overlay.setVisible(True)

    def close_logs_overlay(self):
        self.logs_overlay.setVisible(False)

    def load_logs(self):
        if not self.log_path.exists():
            self.log_path.touch()
        try:
            txt = self.log_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            txt = ""
        # pokaż tylko ostatnie ~10k znaków, żeby nie zabijać GUI
        if len(txt) > 10000:
            txt = txt[-10000:]
        self.logs_editor.setPlainText(txt)
        self.logs_editor.moveCursor(self.logs_editor.textCursor().End)

    # ---------- OVERLAY "ZAPISANO" ----------

    def show_saved_overlay(self):
        self.saved_label.setVisible(True)
        QTimer.singleShot(900, lambda: self.saved_label.setVisible(False))


# ===================== ENTRYPOINT =====================

def main():
    app = QApplication(sys.argv)
    win = ServerGUI()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
