import sys, os, time, subprocess, atexit
import re
from pathlib import Path
from datetime import datetime, timedelta
import threading  # ← używane przez MapView
from collections import deque
from typing import Optional, List

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView,
    QGraphicsPixmapItem, QGraphicsItem, QMenu, QAction
)
from PyQt5.QtCore import Qt, QRectF, QTimer, QPointF, QProcessEnvironment, QObject, QProcess, QFileSystemWatcher, pyqtSignal
from PyQt5.QtGui import QPixmap, QPen, QPainter, QCursor, QTransform
from PyQt5.QtGui import QPixmap, QPen, QPainter, QCursor, QTransform, QColor
from PyQt5.QtGui import QPainterPath  # ← DODANE dla LineItem
from PyQt5.QtWidgets import QGraphicsLineItem
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QBrush


class Loger:
    COLORS = {"INFO": "\033[92m", "WARN": "\033[93m", "ERROR": "\033[91m", "RESET": "\033[0m",}
    def __init__(self, log_file=None): self.log_file = log_file; self.console = True
    def _write(self, level, msg):
        ts = datetime.now().strftime("%H:%M:%S"); line = f"[{ts}] [{level}] {msg}"
        color = self.COLORS.get(level, ""); reset = self.COLORS["RESET"]
        if self.console: print(f"{color}{line}{reset}")
    def info(self, msg): self._write("INFO", msg)
    def warn(self, msg): self._write("WARN", msg)
    def error(self, msg): self._write("ERROR", msg)
log = Loger()

# =========================
# STAŁE ŚCIEŻEK
# =========================
HERE = Path(__file__).resolve().parent
OPCJE_DIR = HERE / "opcje"
BASE_DIR = HERE.parent
OBJECTS_DIR = BASE_DIR / "obiekty"   # Główny folder obiektów
ICONS_DIR = BASE_DIR / "ikony"
OBRAZ_PATH = BASE_DIR / "obraz.txt"
LINES_DIR = BASE_DIR / "linie"            # główny folder linii
POLACZENIE_PATH = BASE_DIR / "polaczenie.txt"
LINE_SOURCE_CACHE = {}
NOWE_POLACZENIE_DIR = HERE / "nowe_połączenie"
AB_PATH = NOWE_POLACZENIE_DIR / "AB.txt"
DODAWANIE_PY = NOWE_POLACZENIE_DIR / "dodawanie.py"

# 🔥 Ścieżka do menedżera (pojedynczy plik .py uruchamiany przez subprocess)
ZLO_MENAGER_PATH = HERE / "zlo_menager.py"
ZLO_MENAGER_LOG  = HERE / "zlo_menager.log"

# =========================
# CACHE (Mapowanie Obiektów)
# =========================
SOURCE_CACHE = {}

# =========================
# FUNKCJE DANYCH AGENTA (Source Data)
# =========================

_manager_proc = None

def _start_manager():
    """Uruchamia zlo_menager.py jako osobny proces i trzyma go do końca."""
    global _manager_proc
    if _manager_proc is not None:
        return  # już działa w tym procesie

    if not ZLO_MENAGER_PATH.exists():
        log.warn(f"Brak pliku menedżera: {ZLO_MENAGER_PATH}")
        return

    try:
        log.info(f"Start zlo_menager → {ZLO_MENAGER_PATH.name}")
        _manager_proc = subprocess.Popen(
            [sys.executable, str(ZLO_MENAGER_PATH)],
            cwd=str(HERE),
            stdout=open(ZLO_MENAGER_LOG, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            close_fds=os.name != "nt",
            env={**os.environ, "ZLO_MANAGER_PARENT": str(os.getpid())}
        )
    except Exception as e:
        log.error(f"Nie udało się uruchomić zlo_menager.py: {e}")
        _manager_proc = None
        return

    def _shutdown():
        try:
            if _manager_proc and _manager_proc.poll() is None:
                _manager_proc.terminate()
                _manager_proc.wait(timeout=5)
        except Exception:
            pass

    atexit.register(_shutdown)

# auto-start przy imporcie (tylko raz na proces)
_start_manager()


def parse_source_file(path: Path, lines: list, agent_folder: str = ""):
    """Parsuje zawartość pojedynczego pliku/linii źródłowej do formatu danych.
    
    ZASADY:
    - obraz.txt: KAŻDA linia = JEDEN obiekt, pola oddzielone '|' (np. xy=-2773 -127|ikona=agent/agent|rozmiar=1|proces=on)
    - plik multi-line (np. mapa_dane.txt): wiele linii key=value
    - plik single-line: jedna linia 'xy=...|...' albo sama 'xy=...'
    """
    data_list = []

    # Specjalny tryb dla obraz.txt — zawsze 1 linia = 1 obiekt
    if path.name.lower() == "obraz.txt":
        for i, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line:
                continue
            # rozbij na klucze
            parts = [p for p in line.split('|') if p.strip()]
            data = {}
            for part in parts:
                if '=' in part:
                    k, v = part.split('=', 1)
                    data[k.strip().lower()] = v.strip()
            # wymagane: xy
            xy_val = data.get('xy', '0 0').strip()
            xy_parts = re.split(r'[\s,]+', xy_val)
            x = float(xy_parts[0]) if xy_parts and xy_parts[0] else 0.0
            y = float(xy_parts[1]) if len(xy_parts) > 1 and xy_parts[1] else 0.0
            size = data.get('rozmiar', '1')
            try:
                size = float(str(size).replace(',', '.'))
            except:
                size = 1.0

            data_list.append({
                "x": x, "y": y,
                "ikona": data.get("ikona", ""),
                "rozmiar": str(max(0.01, float(size))),
                "proces": data.get("proces", "").lower(),
                "file": str(path), "line_no": i, "raw_line": raw_line,
                "is_source_multi": False, "agent_folder": agent_folder
            })
        return data_list

    # Heurystyka do odróżnienia formatu multi-line od single-line
    is_multi_line_format = (len(lines) > 1 and all('=' in line for line in lines)) or                            (len(lines) == 1 and not lines[0].strip().lower().startswith('xy='))

    if is_multi_line_format:
        # Format: plik konfiguracyjny (obiekt_A.txt, mapa_dane.txt multi-line)
        data = {}
        for line in lines:
            if '=' in line:
                key, val = line.split('=', 1)
                data[key.strip().lower()] = val.strip()

        # xy: pozwól na spacje/przecinki i minusy
        xy_val = data.get("xy", "0 0")
        xy = re.split(r'[\s,]+', xy_val.strip())
        x = float(xy[0].strip()) if xy[0].strip() else 0.0
        y = float(xy[1].strip()) if len(xy) > 1 and xy[1].strip() else 0.0

        size = 1.0
        if "rozmiar" in data:
            try:
                size = float(str(data["rozmiar"]).replace(",", "."))
            except ValueError:
                pass

        data_list.append({
            "x": x, "y": y, "ikona": data.get("ikona", ""),
            "rozmiar": str(max(0.01, size)), "proces": data.get("proces", "").lower(),
            "file": str(path), "line_no": 1, "raw_line": "\n".join(lines),
            "is_source_multi": True, "agent_folder": agent_folder
        })
    else:
        # Single-line: 'xy=...|ikona=...|...'
        for i, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line:
                continue
            data = {}
            parts = [p for p in line.split('|') if p.strip()]
            for part in parts:
                if '=' in part:
                    k, v = part.split('=', 1)
                    data[k.strip().lower()] = v.strip()

            xy_val = data.get("xy", "0 0")
            xy = re.split(r'[\s,]+', xy_val.strip())
            data_list.append({
                "x": float(xy[0].strip()) if xy[0].strip() else 0.0,
                "y": float(xy[1].strip()) if len(xy)>1 and xy[1].strip() else 0.0,
                "ikona": data.get('ikona', ''),
                "rozmiar": str(max(0.01, float(str(data.get('rozmiar','1')).replace(',','.')))),
                "proces": data.get('proces', '').lower(),
                "file": str(path), "line_no": i, "raw_line": raw_line,
                "is_source_multi": False, "agent_folder": agent_folder
            })

    return data_list

def load_source_data():
    """Wczytuje surowe dane ze WSZYSTKICH folderów agentów w obiekty/."""
    global SOURCE_CACHE
    SOURCE_CACHE = {}
    
    if not OBJECTS_DIR.exists():
        log.error(f"Folder obiektów nie istnieje: {OBJECTS_DIR}")
        return []

    final_data_list = []
    
    # Przeszukaj wszystkie foldery w obiekty/
    for agent_folder in OBJECTS_DIR.iterdir():
        if not agent_folder.is_dir():
            continue
            
        log.info(f"Ładuję dane z agenta: {agent_folder.name}")
        
        # SPRAWDŹ RÓŻNE MOŻLIWOŚCI:
        data_paths = []
        
        # Opcja 1: Plik mapa_dane.txt bezpośrednio w folderze agenta
        mapa_dane_file = agent_folder / "mapa_dane.txt"
        if mapa_dane_file.exists():
            data_paths.append(mapa_dane_file)
            log.info(f"Znaleziono plik: {mapa_dane_file}")
        
        # Przetwórz znalezione pliki
        for path in data_paths:
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                source_items = parse_source_file(path, lines, agent_folder.name)
                
                for item in source_items:
                    key = (item.get('ikona'), item.get('rozmiar'), item.get('proces'), 
                           item.get('file'), item.get('line_no'), item.get('agent_folder'))
                    SOURCE_CACHE[key] = item
                    final_data_list.append(item)
                    
            except Exception as e:
                log.error(f"Błąd odczytu pliku {path.name}: {e}")
                
    log.info(f"Załadowano dane z {len(final_data_list)} obiektów z {len(list(OBJECTS_DIR.iterdir()))} agentów")
    return final_data_list

def write_obraz(source_data_list, output_path: Path = OBRAZ_PATH):
    """Generuje plik tekstowy obraz.txt (podsumowanie) z danych źródłowych."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for data in source_data_list:
                x = int(round(data.get('x', 0))); y = int(round(data.get('y', 0)))
                ikona = data.get('ikona', ''); rozmiar = data.get('rozmiar', '1')
                proces = data.get('proces', '')
                f.write(f"xy={x} {y}|ikona={ikona}|rozmiar={rozmiar}|proces={proces}\n")
        log.info(f"Zapisano podsumowanie do: {output_path}")
    except Exception as e:
        log.error(f"Nie udało się zapisać pliku {output_path}: {e}")

# =========================
# L I N I E  —  DODANE
# =========================

def parse_line_source_file(path: Path, lines: list, line_folder: str = ""):
    """
    linia_dane.txt (multi-line):
      xy1= x y
      xy2= x y
      proces= off|on|error|lag|old
    """
    data = {}
    for line in lines:
        if '=' in line:
            k, v = line.split('=', 1)
            data[k.strip().lower()] = v.strip()

    def _xy(s, default="0 0"):
        parts = re.split(r'[\s,]+', (s or default))
        x = float(parts[0]) if parts and parts[0] else 0.0
        y = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
        return x, y

    x1, y1 = _xy(data.get("xy1"))
    x2, y2 = _xy(data.get("xy2"))
    return [{
        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
        "proces": (data.get("proces","").lower()),
        "file": str(path), "is_source_multi": True, "line_folder": line_folder
    }]

def load_line_source_data():
    """Wczytuje dane linii z /linie/*/linia_dane* (wiele plików na folder)."""
    global LINE_SOURCE_CACHE
    LINE_SOURCE_CACHE = {}
    if not LINES_DIR.exists():
        return []
    out = []
    for line_dir in LINES_DIR.iterdir():
        if not line_dir.is_dir():
            continue
        # bierzemy wszystko co zaczyna się od 'linia_dane' (z lub bez rozszerzenia)
        cfg_list = sorted([
            p for p in line_dir.iterdir()
            if p.is_file() and p.name.lower().startswith("linia_dane")
        ], key=lambda p: p.name.lower())

        if not cfg_list:
            continue

        for cfg in cfg_list:
            try:
                lines = cfg.read_text(encoding="utf-8", errors="replace").splitlines()
                items = parse_line_source_file(cfg, lines, line_dir.name)
                for it in items:
                    key = (it["x1"], it["y1"], it["x2"], it["y2"], it["proces"], it["line_folder"], cfg.name)
                    LINE_SOURCE_CACHE[key] = it
                    out.append(it)
            except Exception as e:
                log.warn(f"Linie: błąd odczytu {cfg}: {e}")
    return out

def write_polaczenie(line_source_list, output_path: Path = POLACZENIE_PATH):
    """Zapisuje podsumowanie linii (jak obraz.txt dla obiektów). Jedna linia = jedna linia na mapie."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for d in line_source_list:
                x1, y1 = int(round(d.get("x1",0))), int(round(d.get("y1",0)))
                x2, y2 = int(round(d.get("x2",0))), int(round(d.get("y2",0)))
                proces = d.get("proces","")
                f.write(f"xy1={x1} {y1}|xy2={x2} {y2}|proces={proces}\n")
        log.info(f"Zapisano polaczenie.txt → {output_path}")
    except Exception as e:
        log.error(f"Nie udało się zapisać {output_path}: {e}")

def load_line_display_data(path: Path = POLACZENIE_PATH):
    """Wczytuje dane do rysowania linii z polaczenie.txt."""
    out = []
    if not path.is_file():
        return out
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for raw in lines:
            raw = raw.strip()
            if not raw:
                continue
            parts = [p for p in raw.split('|') if p.strip()]
            data = {}
            for p in parts:
                if '=' in p:
                    k,v = p.split('=',1)
                    data[k.strip().lower()] = v.strip()
            def _xy(s):
                ps = re.split(r'[\s,]+', (s or "0 0"))
                x = float(ps[0]) if ps and ps[0] else 0.0
                y = float(ps[1]) if len(ps)>1 and ps[1] else 0.0
                return x, y
            x1,y1 = _xy(data.get("xy1"))
            x2,y2 = _xy(data.get("xy2"))
            out.append({
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "proces": (data.get("proces","").lower())
            })
    except Exception as e:
        log.error(f"Błąd odczytu polaczenie.txt: {e}")
    return out

class TempDragLineItem(QGraphicsLineItem):
    def __init__(self, x1, y1, x2, y2):
        super().__init__(x1, y1, x2, y2)
        pen = QPen(QColor(255, 255, 255))
        pen.setWidthF(2.0)           # cienka jak OFF
        pen.setCosmetic(True)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)
        self.setZValue(0)            # pod ikonami
        self.setAcceptedMouseButtons(Qt.NoButton)  # nie przechwytuje eventów

# ——— Rysowanie linii: QGraphicsItem ———
class LineItem(QGraphicsItem):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.setAcceptHoverEvents(True)
        self.setZValue(0)  # pod ikonami

        self._path = QPainterPath()
        self._x1 = float(data.get("x1",0)); self._y1 = float(data.get("y1",0))
        self._x2 = float(data.get("x2",0)); self._y2 = float(data.get("y2",0))
        self._rebuild_path()

    def _rebuild_path(self):
        self._path = QPainterPath()
        self._path.moveTo(self._x1, self._y1)
        self._path.lineTo(self._x2, self._y2)

    def boundingRect(self):
        return self._path.boundingRect().adjusted(-8, -8, 8, 8)

    def shape(self):
        # grubszy hitbox dla łatwego hovera/kliknięcia (używamy samej ścieżki jako shape)
        return self._path

    def hoverEnterEvent(self, event):
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.update()
        super().hoverLeaveEvent(event)

    def paint(self, painter: QPainter, option, widget=None):
        proces = (self.data.get("proces","") or "").strip().lower()
        hover = self.isUnderMouse()

        # mapa kolorów procesu
        if proces in ("", "off", "none"):
            pen_color = QColor(255, 255, 255)  # „niewidoczna”
            pen_width = 2.0
            if hover:  # tylko przy off świeci niebieskim
                pen_color = QColor(0, 122, 255)
        elif proces == "on":
            pen_color = Qt.green
            pen_width = 6.0
        elif proces == "error":
            pen_color = Qt.red
            pen_width = 6.0
        elif proces == "lag":
            pen_color = QColor(255, 152, 0)
            pen_width = 6.0
        elif proces == "old":
            pen_color = QColor(144, 238, 144)
            pen_width = 6.0
        else:
            pen_color = QColor(200, 200, 200)
            pen_width = 6.0

        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(pen_color)
        pen.setCosmetic(True)
        pen.setWidthF(pen_width)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(self._path)

# =========================
# FUNKCJE DO WYSZUKIWANIA I AKTUALIZACJI PLIKÓW
# =========================

def find_files_with_xy(target_x: float, target_y: float, target_agent: str = ""):
    """Znajduje pliki z podanymi współrzędnymi w odpowiednim folderze agenta."""
    matching_files = []
    
    try:
        # Szukamy w folderze odpowiedniego agenta
        if target_agent:
            agent_path = OBJECTS_DIR / target_agent
            if agent_path.exists():
                search_paths = [agent_path]
            else:
                log.error(f"Folder agenta nie istnieje: {agent_path}")
                return []
        else:
            # Jeśli nie znamy agenta, szukamy we wszystkich
            search_paths = [agent_folder for agent_folder in OBJECTS_DIR.iterdir() 
                          if agent_folder.is_dir()]

        for agent_path in search_paths:
            # Sprawdź wszystkie możliwe lokalizacje plików
            possible_locations = []
            
            # Plik mapa_dane.txt
            mapa_dane_file = agent_path / "mapa_dane.txt"
            if mapa_dane_file.exists():
                possible_locations.append(mapa_dane_file)
            
            # Folder mapa_dane
            mapa_dane_folder = agent_path / "mapa_dane"
            if mapa_dane_folder.exists():
                for file_path in mapa_dane_folder.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in ('.txt', ''):
                        possible_locations.append(file_path)
            
            # Wszystkie pliki .txt w folderze agenta
            for file_path in agent_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() == '.txt':
                    if file_path not in possible_locations:
                        possible_locations.append(file_path)

            # Przeszukaj znalezione pliki
            for file_path in possible_locations:
                try:
                    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()
                        if not line:
                            continue
                        
                        if 'xy=' in line.lower():
                            data = {}
                            parts = line.split("|")
                            for part in parts:
                                if "=" in part:
                                    k, v = part.split("=", 1)
                                    data[k.strip().lower()] = v.strip()
                            
                            if "xy" in data:
                                xy_parts = data["xy"].replace(",", " ").split()
                                if len(xy_parts) >= 2:
                                    try:
                                        x = float(xy_parts[0])
                                        y = float(xy_parts[1])
                                        
                                        if abs(x - target_x) < 0.1 and abs(y - target_y) < 0.1:
                                            matching_files.append({
                                                'file': file_path,
                                                'line_num': line_num,
                                                'line_content': line,
                                                'x': x,
                                                'y': y,
                                                'agent': agent_path.name
                                            })
                                            log.info(f"Znaleziono pasujący plik: {file_path.name}")
                                    except ValueError:
                                        continue
                except Exception as e:
                    log.error(f"Błąd odczytu pliku {file_path}: {e}")
                    continue
                
    except Exception as e:
        log.error(f"Błąd przeszukiwania folderów: {e}")
    
    return matching_files

def update_xy_in_files(matching_files, new_x: float, new_y: float):
    """Aktualizuje współrzędne xy w znalezionych plikach."""
    updated_count = 0
    
    for file_info in matching_files:
        file_path = file_info['file']
        line_num = file_info['line_num']
        old_line = file_info['line_content']
        
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            
            if line_num - 1 < len(lines):
                old_line = lines[line_num - 1]
                
                if 'xy=' in old_line.lower():
                    new_xy_part = f"xy={int(round(new_x))} {int(round(new_y))}"
                    
                    parts = old_line.split("|")
                    new_parts = []
                    
                    for part in parts:
                        if part.strip().lower().startswith("xy="):
                            new_parts.append(new_xy_part)
                        else:
                            new_parts.append(part)
                    
                    new_line = "|".join(new_parts)
                    lines[line_num - 1] = new_line
                    
                    file_path.write_text('\n'.join(lines), encoding="utf-8")
                    updated_count += 1
                    log.info(f"Zaktualizowano pozycję w: {file_path.name}")
            
        except Exception as e:
            log.error(f"Błąd aktualizacji pliku {file_path}: {e}")
    
    return updated_count

# =========================
# FUNKCJA WCZYTUJĄCA DANE DO WIDOKU (z obraz.txt)
# =========================

def load_display_data(path: Path = OBRAZ_PATH):
    """Wczytuje dane do wyświetlenia z obraz.txt i łączy je z danymi źródłowymi po XY (z tolerancją)."""
    display_data_list = []
    if not path.is_file():
        return []

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        data_from_obraz = parse_source_file(path, lines)

        # tolerancja na dryf zapisu/zaokrąglenia
        TOL = 0.51

        for data in data_from_obraz:
            x = float(data.get('x', 0.0))
            y = float(data.get('y', 0.0))

            source_data_match = None
            best_dist = 1e9

            # SZUKAJ PO XY w SOURCE_CACHE (to są dane z prawdziwych folderów)
            for source_item in SOURCE_CACHE.values():
                sx = float(source_item.get('x', 0.0))
                sy = float(source_item.get('y', 0.0))
                dx = abs(sx - x)
                dy = abs(sy - y)
                if dx <= TOL and dy <= TOL:
                    # jeśli kilka w tolerancji — bierz najbliższy
                    d = dx + dy
                    if d < best_dist:
                        best_dist = d
                        source_data_match = source_item

            if source_data_match:
                data['original_source_data'] = source_data_match
                data['agent_folder'] = source_data_match.get('agent_folder', '')
                display_data_list.append(data)
            else:
                # zostaw loga diagnostycznego — to pomoże gdy coś nie wejdzie w tolerancję
                log.warn(f"Brak matcha po XY dla: x={x} y={y}")

    except Exception as e:
        log.error(f"Błąd odczytu obraz.txt: {e}")

    return display_data_list

# =========================
# KLASY GUI I LOGIKA ZAPISU (Drag & Drop)
# =========================

class MapItem(QGraphicsPixmapItem):
    """
    Ikona obiektu na mapie:
    - drag z aktualizacją XY w plikach (dwukierunkowa synchronizacja)
    - kolorowa ramka procesu (on/error)
    - PPM → menu opcji z <AGENT_DIR>/opcje/*
    """

    def __init__(self, pixmap, data,
                 sensor_dir: Path, sensor_lock, sensor_write_fn,
                 base_dir: Path, objects_dir: Path):
        super().__init__(pixmap)
        self.data = data
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setZValue(1)

        source_data = data.get('original_source_data', {}) or {}
        self.original_x = data.get('x', 0)
        self.original_y = data.get('y', 0)

        # referencje systemowe
        self._sensor_dir = sensor_dir
        self._sensor_lock = sensor_lock
        self._sensor_write = sensor_write_fn
        self._base_dir = base_dir
        self._objects_dir = objects_dir

        # jeśli w danych już był folder agenta — zapamiętaj
        agent_name = (source_data.get('agent_folder', '') or '').strip()
        self.agent_dir = (self._objects_dir / agent_name) if agent_name else None

        # stan przytrzymania / drag
        self._press_state = {"lp": {"pos": None, "ts": None}, "pp": {"pos": None, "ts": None}}
        self._dragging = False
        self._snap_on_hover = True
        self._hover_target_item = None
        self._temp_line_start_item = None
    # === RYSOWANIE ===
    def boundingRect(self):
        br = super().boundingRect()
        extra = 1.0
        expanded = QRectF(br.x() - extra, br.y() - extra, br.width() + extra * 2, br.height() + extra * 2)
        return br.united(expanded)

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        proces = (self.data.get('proces', '') or '').strip().lower()

        # mapa kolorów dla wszystkich stanów
        color_map = {
            "on": Qt.green,                 # zielony
            "error": Qt.red,                # czerwony
            "lag": QColor(255, 152, 0),     # pomarańcz
            "old": QColor(144, 238, 144),   # jasna zieleń
        }

        color = color_map.get(proces)
        if not color:
            return  # brak obwódki dla pustych lub nieznanych stanów

        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(color)
        pen.setWidthF(12.0)
        pen.setCosmetic(True)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        rect = super().boundingRect().adjusted(25, 25, -25, -25)
        painter.drawEllipse(rect)

    # === MENU OPCJI (PPM) ===
    def contextMenuEvent(self, event):
        # jeśli właśnie rysujemy gumkę po 2×PPM, to NIE pokazuj menu
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if view and getattr(view, "_temp_line_active", False):
            event.accept()
            return

        # 🔒 jeśli widok ustawił tłumik po PPM-drag/gumce — zgaś JEDEN kontekst
        if view and getattr(view, "_suppress_next_pp_context", False):
            view._suppress_next_pp_context = False
            event.accept()
            return

        scene_pos = event.scenePos()
        self._show_context_menu(event, scene_pos)
        event.accept()

    def _show_context_menu(self, mouse_event, scene_pos: QPointF):
        menu = QMenu()
        menu.setTitle("Opcje")

        # 🔒 jeśli widok chce stłumić najbliższe menu — wyjdź
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if view and getattr(view, "_suppress_next_pp_context", False):
            view._suppress_next_pp_context = False
            return

        # 🔍 znajdź folder obiektu tak jak w logice drag (po original_x/y)
        agent_dir = self._resolve_agent_dir_from_xy(self.original_x, self.original_y)
        options = self._load_options_from_agent(agent_dir)

        if not options:
            a = QAction("Brak opcji (dodaj foldery w /opcje)", menu)
            a.setEnabled(False)
            menu.addAction(a)
        else:
            for opt_name, gui_path in options:
                action = QAction(opt_name, menu)
                action.triggered.connect(
                    lambda checked=False, n=opt_name, p=gui_path: self._run_option(n, p, scene_pos, agent_dir)
                )
                menu.addAction(action)

        pos = getattr(mouse_event, "screenPos", None)
        if callable(pos):
            pos = pos()
        try:
            menu.exec_(pos.toPoint() if hasattr(pos, "toPoint") else pos)
        except Exception:
            menu.exec_(QCursor.pos())

    def _resolve_agent_dir_from_xy(self, x, y) -> Optional[Path]:
        """Identyczna logika jak przy drag — szuka pliku z danym XY i zwraca folder obiektu."""
        try:
            matches = find_files_with_xy(x, y, None)
            if not matches:
                matches = find_files_with_xy(x, y, "")
            if matches:
                agent_name = matches[0].get('agent', '')
                if agent_name:
                    return self._objects_dir / agent_name
        except Exception as e:
            log.error(f"Błąd wyszukiwania agenta po XY: {e}")
        return None

    def _run_option(self, opt_name: str, gui_path: Path, scene_pos: QPointF, agent_dir: Optional[Path]):
        """Odpala gui.py dla danego agenta"""
        if not gui_path or not gui_path.exists():
            log.warn(f"Opcja '{opt_name}' nie ma gui.py ({gui_path})")
            return

        try:
            proc = QProcess()
            proc.setProgram(sys.executable)
            # python gui.py BASE_DIR OBJECTS_DIR AGENT_DIR
            args = [str(gui_path), str(self._base_dir), str(self._objects_dir)]
            if agent_dir:
                args.append(str(agent_dir))
            proc.setArguments(args)
            proc.startDetached()
            log.info(f"Uruchomiono {gui_path} ({opt_name}) dla {agent_dir}")
        except Exception as e:
            log.error(f"Nie udało się uruchomić opcji '{opt_name}': {e}")

    def _load_options_from_agent(self, agent_dir: Optional[Path]):
        """Czyta <agent_dir>/opcje/*, zwraca [(nazwa, ścieżka_do_gui.py|None)]."""
        opts = []
        try:
            if not agent_dir or not agent_dir.exists():
                return opts
            opts_dir = agent_dir / "opcje"
            if not opts_dir.exists():
                return opts
            for sub in sorted([p for p in opts_dir.iterdir() if p.is_dir()]):
                name = sub.name
                gui_py = sub / "gui.py"
                opts.append((name, gui_py if gui_py.exists() else None))
        except Exception as e:
            log.error(f"Błąd ładowania opcji: {e}")
        return opts

    # === MYSZ / DRAG ===
    def mousePressEvent(self, event):
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            btn = "lp" if event.button() == Qt.LeftButton else "pp"
            self._press_state[btn]["pos"] = (int(event.scenePos().x()), int(event.scenePos().y()))
            self._press_state[btn]["ts"] = datetime.now()
        if event.button() == Qt.LeftButton:
            self._dragging = True
            global MAIN_WINDOW_INSTANCE
            if MAIN_WINDOW_INSTANCE:
                MAIN_WINDOW_INSTANCE.dragging = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            x_center = self.pos().x() + self.pixmap().width() / 2.0
            y_center = self.pos().y() + self.pixmap().height() / 2.0
            matching_files = find_files_with_xy(self.original_x, self.original_y, None)
            if not matching_files:
                matching_files = find_files_with_xy(self.original_x, self.original_y, "")
            if matching_files:
                updated_count = update_xy_in_files(matching_files, x_center, y_center)
                if updated_count > 0:
                    log.info(f"Zaktualizowano {updated_count} plików")
                    load_source_data()
                    write_obraz(list(SOURCE_CACHE.values()))
                    self.original_x, self.original_y = x_center, y_center
                else:
                    log.warn("Nie zaktualizowano żadnego pliku — linia z xy nieznaleziona?")
            else:
                log.warn(f"Nie znaleziono plików z pozycją: ({self.original_x},{self.original_y})")
            global MAIN_WINDOW_INSTANCE
            if MAIN_WINDOW_INSTANCE:
                MAIN_WINDOW_INSTANCE.dragging = False
                MAIN_WINDOW_INSTANCE.refresh()
            self._dragging = False
        
class MapView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._snap_on_hover = True
        self._hover_target_item = None
        self._temp_line_start_item = None
        self.setDragMode(QGraphicsView.NoDrag)
        self._panning = False
        self._pan_start = None
        self.setRenderHints(self.renderHints() | QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(Qt.NoBrush))
        self.setStyleSheet("QGraphicsView { border: none; background: transparent; }")
        self._pan_sensitivity = 0.8
        self._rpress_can_draw_line = False  # linia gumka tylko gdy PP start na obiekcie

        # --- NOWE: tłumik jednorazowy kontekstów po PPM-drag ---
        self._suppress_next_pp_context = False

        # ====== SENSORY ======
        import threading
        self._sensor_lock = threading.Lock()
        self._sensor_press = {"lp": {"pos": None, "ts": None}, "pp": {"pos": None, "ts": None}}
        self._sensor_dir = HERE / "sensory"
        try:
            self._sensor_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"Sensory: folder OK -> {self._sensor_dir}")
        except Exception as e:
            log.error(f"Sensory: nie mogę utworzyć folderu: {e}")

        # ====== GUMKA – linia tymczasowa (wizualna) ======
        self._temp_line_active = False
        self._temp_line_item = None
        self._temp_line_start = None  # QPointF

        # ====== PPM press/drag detection ======
        self._rpress_active = False
        self._rpress_start_viewpos = None
        self._rpress_start_scenepos = None
        self._rpress_item_at_press = None
        self._drag_threshold_px = 6  # minimalny ruch, żeby uznać za „przeciąganie”
        self._pp_dragged = False  # czy był ruch PPM powyżej progu
        
    def drawBackground(self, painter, rect):
        try:
            # ============================
            # 🔥 HOT RELOAD zmiana.txt
            # ============================
            bg_watch = HERE / "tapety" / "zmiana.txt"
            new_mtime = bg_watch.stat().st_mtime if bg_watch.exists() else None

            if new_mtime != getattr(self, "_bg_last_mtime", None):
                self._bg_last_mtime = new_mtime
                self._bg_force_reload = True

            # ============================
            # 🔥 ŁADOWANIE TAPETY
            # ============================
            if not hasattr(self, "_bg_cache") or getattr(self, "_bg_force_reload", True):

                bg_dir = HERE / "tapety"
                bg_path = None

                for name in ["tło.png", "tlo.png", "tło.jpg", "tlo.jpg",
                            "background.png", "background.jpg"]:
                    p = bg_dir / name
                    if p.exists():
                        bg_path = p
                        break

                if bg_path:
                    pm = QPixmap(str(bg_path))
                    if not pm.isNull():
                        self._bg_cache = pm

                self._bg_force_reload = False

            if not hasattr(self, "_bg_cache") or self._bg_cache is None:
                return

            pm = self._bg_cache

            # ============================
            # 🔥 KLUCZ: rysujemy względem VIEWPORT, nie SCENY
            # ============================
            view_w = self.viewport().width()
            view_h = self.viewport().height()

            scaled = pm.scaled(
                view_w,
                view_h,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )

            # Wyłącz transformacje sceny → tło jest SZTYWNE
            painter.resetTransform()

            # Rysujemy tapetę zawsze od (0,0) viewportu
            painter.drawPixmap(0, 0, scaled)

        except Exception as e:
            print(f"[WARN] drawBackground: {e}")

    # ====== ZOOM ======
    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        factor = 1.0015 ** angle
        self.scale(factor, factor)
        event.accept()

    # ====== MYSZ ======
    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())

        # PPM: przygotuj tryb click-vs-drag
        if event.button() == Qt.RightButton:
            self._rpress_active = True
            self._rpress_start_viewpos = event.pos()
            self._rpress_start_scenepos = scene_pos
            self._rpress_item_at_press = self.itemAt(event.pos())

            # rysować gumkę wolno TYLKO gdy start był na MapItem (obiekt)
            from PyQt5.QtWidgets import QGraphicsItem
            self._rpress_can_draw_line = isinstance(self._rpress_item_at_press, MapItem)

            # log sensory (jak było)
            self._sensor_press["pp"]["pos"] = (int(round(scene_pos.x())), int(round(scene_pos.y())))
            self._sensor_press["pp"]["ts"] = datetime.now()
            self._sensor_write("pp", {
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "event": "pp",
                "button": "pp",
                "start": f"{self._sensor_press['pp']['pos'][0]} {self._sensor_press['pp']['pos'][1]}",
            })
            event.accept()
            return

        # MMB → pan
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        # LP log sensory
        if event.button() == Qt.LeftButton:
            self._sensor_press["lp"]["pos"] = (int(round(scene_pos.x())), int(round(scene_pos.y())))
            self._sensor_press["lp"]["ts"] = datetime.now()
            self._sensor_write("lp", {
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "event": "lp",
                "button": "lp",
                "start": f"{self._sensor_press['lp']['pos'][0]} {self._sensor_press['lp']['pos'][1]}",
            })

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Jeśli trwa tryb PPM i jeszcze nie rysujemy, sprawdź threshold
        if self._rpress_active and not self._temp_line_active:
            delta = event.pos() - self._rpress_start_viewpos
            if abs(delta.x()) >= self._drag_threshold_px or abs(delta.y()) >= self._drag_threshold_px:
                self._pp_dragged = True
                if self._rpress_can_draw_line:
                    # 🔥 gumka startuje z CENTRUM obiektu, na którym zaczęto PPM
                    self._start_temp_line(self._rpress_start_scenepos, start_item=self._rpress_item_at_press)
                else:
                    # drag z tła: bez gumki, tłumimy ewentualne menu
                    self._suppress_next_pp_context = True
                    event.accept()
                return

        # Aktualizacja końcówki gumki
        if self._temp_line_active and self._temp_line_item is not None:
            self._update_temp_line(event.pos())
            event.accept()
            return

        # Pan MMB
        if self._panning and self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            dx = int(delta.x() * self._pan_sensitivity)
            dy = int(delta.y() * self._pan_sensitivity)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
            event.accept()
            return

        super().mouseMoveEvent(event)
  
    def mouseDoubleClickEvent(self, event):
        scene_pos = self.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            # 2xLP → sygnał do modułu dodawania (sensory)
            self._sensor_write("2xlp", {
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "event": "2xlp",
                "button": "lp",
                "start": f"{int(round(scene_pos.x()))} {int(round(scene_pos.y()))}",
            })
            event.accept()
            return

        # (PPM nie używamy do dblclick w nowej logice, ale jak masz – zostaw)
        super().mouseDoubleClickEvent(event)
        
    def mouseReleaseEvent(self, event):
        scene_pos = self.mapToScene(event.pos())

        # Domknięcie logów LP/PP
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            btn = "lp" if event.button() == Qt.LeftButton else "pp"
            end_pos = (int(round(scene_pos.x())), int(round(scene_pos.y())))
            start_pos = self._sensor_press[btn]["pos"]
            start_ts  = self._sensor_press[btn]["ts"]
            if start_pos is not None and start_ts is not None:
                dur = max(0.0, (datetime.now() - start_ts).total_seconds())
                self._sensor_write("przytrzymanie", {
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "event": "przytrzymanie",
                    "button": btn,
                    "start": f"{start_pos[0]} {start_pos[1]}",
                    "end":   f"{end_pos[0]} {end_pos[1]}",
                    "czas_s": f"{dur:.6f}",
                })
            self._sensor_write("puszczenie", {
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "event": "puszczenie",
                "button": btn,
                "start": f"{start_pos[0]} {start_pos[1]}" if start_pos else "",
                "end":   f"{end_pos[0]} {end_pos[1]}",
            })
            self._sensor_press[btn]["pos"] = None
            self._sensor_press[btn]["ts"]  = None

        # PPM: zakończ — albo linia, albo menu
        if event.button() == Qt.RightButton:
            # jeśli rysowaliśmy linię → sprzątnij i NIE pokazuj menu (tłumik)
            if self._temp_line_active:
                # 🔑 ustaw tłumik PRZED zgaszeniem linii
                self._suppress_next_pp_context = True
                self._end_temp_line()
                self._rpress_active = False
                self._rpress_item_at_press = None
                self._rpress_can_draw_line = False
                self._pp_dragged = False
                event.accept()
                return

            # jeśli był DRAG PPM (bez gumki) → też tłumimy następne menu
            if getattr(self, "_pp_dragged", False):
                self._suppress_next_pp_context = True
                self._rpress_active = False
                self._rpress_item_at_press = None
                self._pp_dragged = False
                self._rpress_can_draw_line = False
                event.accept()
                return

            # jeśli NIE było dragu → to był „klik” → ewentualne menu
            item = self._rpress_item_at_press
            view_pos = self._rpress_start_viewpos
            scene_pos_press = self._rpress_start_scenepos
            self._rpress_active = False
            self._rpress_item_at_press = None
            self._rpress_can_draw_line = False

            if item is not None:
                # jeśli to MapItem i ma helper _show_context_menu → odpal jego menu
                try:
                    if isinstance(item, MapItem) and hasattr(item, "_show_context_menu"):
                        gp = self.mapToGlobal(view_pos)
                        class _EvtProxy:
                            def __init__(self, gpos): self._g = gpos
                            def screenPos(self): return self._g
                        # 🔒 JEŚLI tłumik aktywny – nie pokazuj menu
                        if self._suppress_next_pp_context:
                            self._suppress_next_pp_context = False
                            event.accept()
                            return
                        item._show_context_menu(_EvtProxy(gp), scene_pos_press)
                        event.accept()
                        return
                except Exception:
                    pass

            # w przeciwnym razie: menu mapy (też respektuj tłumik)
            class _MouseEventProxy:
                def __init__(self, p): self._p = p
                def pos(self): return self._p
            if self._suppress_next_pp_context:
                self._suppress_next_pp_context = False
                event.accept()
                return
            self._show_context_menu(_MouseEventProxy(view_pos), scene_pos_press)
            event.accept()
            return

        # MMB → koniec pan
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self._pan_start = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)


    # ====== MENU OPCJI (PPM) ======
    def _show_context_menu(self, mouse_event, scene_pos: QPointF):
        # 🔒 globalny tłumik jednorazowy po PPM-drag/gumce
        if getattr(self, "_suppress_next_pp_context", False):
            self._suppress_next_pp_context = False
            return

        # BLOKADA MENU, gdy aktywna gumka (rysowanie linii)
        if getattr(self, "_temp_line_active", False):
            return

        menu = QMenu(self)
        menu.setTitle("Opcje")

        options = self._load_options()
        if not options:
            a = QAction("Brak opcji (dodaj foldery w /opcje)", self)
            a.setEnabled(False)
            menu.addAction(a)
        else:
            for opt_name, gui_path in options:
                action = QAction(opt_name, self)
                action.triggered.connect(lambda checked=False, n=opt_name, p=gui_path: self._run_option(n, p, scene_pos))
                menu.addAction(action)

        menu.exec_(self.mapToGlobal(mouse_event.pos()))

    def _load_options(self):
        opts = []
        try:
            if not OPCJE_DIR.exists():
                log.warn(f"Brak folderu opcji: {OPCJE_DIR}")
                return opts
            for sub in sorted([p for p in OPCJE_DIR.iterdir() if p.is_dir()]):
                name = sub.name
                gui_py = sub / "gui.py"
                opts.append((name, gui_py if gui_py.exists() else None))
        except Exception as e:
            log.error(f"Błąd ładowania opcji: {e}")
        return opts

    def _run_option(self, opt_name: str, gui_path: Path, scene_pos: QPointF):
        x = int(round(scene_pos.x()))
        y = int(round(scene_pos.y()))
        log.info(f"Opcja '{opt_name}' @ xy=({x},{y})")

        if gui_path is None or not gui_path.exists():
            log.warn(f"Opcja '{opt_name}' nie ma gui.py ({OPCJE_DIR/opt_name})")
            return

        try:
            proc = QProcess(self)
            proc.setProgram(sys.executable)
            proc.setArguments([str(gui_path), str(x), str(y), str(BASE_DIR), str(OBJECTS_DIR)])
            proc.startDetached()
        except Exception as e:
            log.error(f"Nie udało się uruchomić opcji '{opt_name}': {e}")

    # ====== SENSORY: zapis (ostatni stan) ======
    def _sensor_write(self, kind: str, fields: dict):
        file_map = {
            "lp": "lp.txt",
            "2xlp": "2xlp.txt",
            "pp": "pp.txt",
            "2xpp": "2xpp.txt",
            "przytrzymanie": "przytrzymanie.txt",
            "puszczenie": "puszczenie.txt",
        }
        name = file_map.get(kind, f"{kind}.txt")
        path = self._sensor_dir / name
        tmp_path = path.with_suffix(".tmp")

        order = ["data", "event", "button", "start", "end", "czas_s"]
        content = "\n".join(f"{k}={fields[k]}" for k in order if k in fields and fields[k] != "") + "\n"

        try:
            with self._sensor_lock:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp_path, path)
        except Exception as e:
            log.warn(f"Sensory: zapis '{name}' nieudany: {e}")

    # ====== GUMKA: helpery ======
    @staticmethod
    def _read_agent_id(agent_dir: Path) -> str:
        if not agent_dir:
            return ""
        try:
            id_file = agent_dir / "id.txt"
            if id_file.exists():
                return (id_file.read_text(encoding="utf-8", errors="replace").strip() or "")
        except Exception:
            pass
        return agent_dir.name if agent_dir else ""
    @staticmethod
    def _as_mapitem(item):
        it = item
        while it is not None and not isinstance(it, MapItem):
            it = it.parentItem()
        return it

    @staticmethod
    def _read_agent_id_from_item(item) -> str:
        it = MapView._as_mapitem(item)
        if it is None:
            return ""
        agent_dir = getattr(it, "agent_dir", None)
        if not agent_dir:
            return ""
        from pathlib import Path
        p = agent_dir if isinstance(agent_dir, Path) else Path(agent_dir)
        try:
            return (p.joinpath("id.txt").read_text(encoding="utf-8", errors="replace").strip() or "")
        except Exception:
            return ""
    def _start_temp_line(self, scene_pos: QPointF, start_item=None):
        if start_item is not None:
            try:
                c = start_item.sceneBoundingRect().center()
                scene_pos = QPointF(c.x(), c.y())
            except Exception:
                pass

        from PyQt5.QtWidgets import QGraphicsLineItem
        self._temp_line_start_item = self._as_mapitem(start_item)
        self._temp_line_start = QPointF(scene_pos.x(), scene_pos.y())
        self._temp_line_item = QGraphicsLineItem(scene_pos.x(), scene_pos.y(),
                                                scene_pos.x(), scene_pos.y())
        pen = QPen(QColor(255, 255, 255))
        pen.setWidthF(2.0)
        pen.setCosmetic(True)
        pen.setJoinStyle(Qt.RoundJoin)
        self._temp_line_item.setPen(pen)
        self._temp_line_item.setZValue(0)
        self._temp_line_item.setAcceptedMouseButtons(Qt.NoButton)
        if self.scene() is not None:
            self.scene().addItem(self._temp_line_item)
        self._temp_line_active = True
        self.setCursor(Qt.CrossCursor)

    def _update_temp_line(self, view_pos):
            if not (self._temp_line_active and self._temp_line_start is not None):
                return

            sp = self.mapToScene(view_pos)
            x1, y1 = self._temp_line_start.x(), self._temp_line_start.y()

            # domyślnie – wolny koniec
            end_x, end_y = sp.x(), sp.y()

            # SNAP: jeśli kursor jest nad obiektem, ustaw koniec na jego środek
            if self._snap_on_hover:
                try:
                    hovered = self.itemAt(QPoint(int(view_pos.x()), int(view_pos.y())))
                    hovered = self._as_mapitem(hovered)
                except TypeError:
                    # w razie gdy view_pos nie jest QPoint
                    hovered = self.itemAt(QPoint(view_pos.x(), view_pos.y()))

                if hovered is not None and hovered is not self._temp_line_item and hovered is not self._temp_line_start_item:
                    try:
                        c = hovered.sceneBoundingRect().center()
                        end_x, end_y = c.x(), c.y()
                        self._hover_target_item = hovered
                    except Exception:
                        self._hover_target_item = None
                else:
                    self._hover_target_item = None

            try:
                if self._temp_line_item is None or self._temp_line_item.scene() is None:
                    from PyQt5.QtWidgets import QGraphicsLineItem
                    self._temp_line_item = QGraphicsLineItem(x1, y1, x1, y1)
                    pen = QPen(QColor(255, 255, 255))
                    pen.setWidthF(2.0)
                    pen.setCosmetic(True)
                    pen.setJoinStyle(Qt.RoundJoin)
                    self._temp_line_item.setPen(pen)
                    self._temp_line_item.setZValue(0)
                    self._temp_line_item.setAcceptedMouseButtons(Qt.NoButton)
                    if self.scene() is not None:
                        self.scene().addItem(self._temp_line_item)

                self._temp_line_item.setLine(x1, y1, end_x, end_y)
            except RuntimeError:
                from PyQt5.QtWidgets import QGraphicsLineItem
                self._temp_line_item = QGraphicsLineItem(x1, y1, end_x, end_y)
                pen = QPen(QColor(255, 255, 255))
                pen.setWidthF(2.0)
                pen.setCosmetic(True)
                pen.setJoinStyle(Qt.RoundJoin)
                self._temp_line_item.setPen(pen)
                self._temp_line_item.setZValue(0)
                self._temp_line_item.setAcceptedMouseButtons(Qt.NoButton)
                if self.scene() is not None:
                    self.scene().addItem(self._temp_line_item)
    def _end_temp_line(self):
        try:
            # mamy start i end już z linii (środki obiektów)
            start_item = self._as_mapitem(getattr(self, "_temp_line_start_item", None))
            end_item   = self._as_mapitem(getattr(self, "_hover_target_item", None))

            start_id = self._read_agent_id_from_item(start_item)
            end_id   = self._read_agent_id_from_item(end_item)

            if start_id and end_id and start_id != end_id:
                from pathlib import Path
                import sys
                from datetime import datetime
                from PyQt5.QtCore import QProcess

                base = Path(__file__).parent / "nowe_połączenie"
                base.mkdir(exist_ok=True)
                ab_path = base / "AB.txt"

                ab_path.write_text(
                    f"obiekt_A={start_id}\nobiekt_B={end_id}\nts={datetime.now().isoformat()}\n",
                    encoding="utf-8"
                )
                print(f"[INFO] Zapisano AB.txt: {ab_path}")

                # odpal dodawanie.py
                proc = QProcess()
                proc.startDetached(sys.executable, [str(base / "dodawanie.py")])

            else:
                print(f"[WARN] brak ID start lub end: '{start_id}' -> '{end_id}'")

        except Exception as e:
            print(f"[ERR] _end_temp_line: {e}")

        # sprzątanie
        try:
            if self._temp_line_item and self._temp_line_item.scene():
                self.scene().removeItem(self._temp_line_item)
        except RuntimeError:
            pass

        self._temp_line_item = None
        self._temp_line_active = False
        self._temp_line_start = None
        self._hover_target_item = None
        self._temp_line_start_item = None
        self.unsetCursor()

HUGE = QRectF(-10_000_000, -10_000_000, 20_000_000, 20_000_000)

class MainWindow(QMainWindow):
    def refresh(self):
        # nie odświeżaj sceny, gdy aktywna „gumka” (PPM-drag)
        if getattr(self.view, "_temp_line_active", False):
            return
        if getattr(self, 'dragging', False):
            return
        
    # --- publiczny interfejs klasy pozostaje bez zmian ---
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Scena + widok (użyj MapView, bo masz sensory i menu mapy)
        self.scene = getattr(self, 'scene', QGraphicsScene(self))
        self.view = getattr(self, 'view', MapView(self.scene))
        self.setCentralWidget(self.view)
        self.scene.setSceneRect(HUGE)

        # --- stan wewnętrzny do sterowania odświeżaniem ---
        self._bg_last_mtime = None
        self._bg_force_reload = True
        self._bg_cache = None
        self._last_obraz_mtime = None
        self._last_polaczenie_mtime = None  # ← DODANE: śledzenie linii
        self._last_sources_sig = None
        self._dirty_display = False
        self.dragging = getattr(self, 'dragging', False)

        # Priming: załaduj źródła i wygeneruj obraz.txt + polaczenie.txt na starcie
        self._prime_sources_and_obraz()

        # --- timery ---
        # 1) wolny polling źródeł (I/O, ale lekki) – co 1s
        self.sources_timer = QTimer(self)
        self.sources_timer.timeout.connect(self._maybe_regenerate_obraz)
        self.sources_timer.start(1000)

        # 2) szybki repaint bez I/O – co ~0.33s
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(333)

        # startowy mtime obrazów i pierwsze odświeżenie
        try:
            self._last_obraz_mtime = OBRAZ_PATH.stat().st_mtime
        except Exception:
            self._last_obraz_mtime = None
        try:
            self._last_polaczenie_mtime = POLACZENIE_PATH.stat().st_mtime
        except Exception:
            self._last_polaczenie_mtime = None

        self._dirty_display = True

    def _prime_sources_and_obraz(self):
        try:
            # obiekty → obraz.txt
            load_source_data()
            write_obraz(list(SOURCE_CACHE.values()))
            # linie → polaczenie.txt
            load_line_source_data()
            write_polaczenie(list(LINE_SOURCE_CACHE.values()))

            self._last_sources_sig = self._sources_signature()
            try:
                self._last_obraz_mtime = OBRAZ_PATH.stat().st_mtime
            except Exception:
                self._last_obraz_mtime = None
            try:
                self._last_polaczenie_mtime = POLACZENIE_PATH.stat().st_mtime
            except Exception:
                self._last_polaczenie_mtime = None

            self._dirty_display = True
        except Exception:
            pass

    # --- sygnatura źródeł: mtimes/rozmiary obiekty/*/mapa_dane.txt + linie/*/linia_dane.txt ---
    def _sources_signature(self):
        sig = []
        try:
            if OBJECTS_DIR and OBJECTS_DIR.exists():
                for agent in OBJECTS_DIR.iterdir():
                    if agent.is_dir():
                        f = agent / 'mapa_dane.txt'
                        if f.exists():
                            st = f.stat()
                            sig.append((str(f), st.st_mtime, st.st_size))
            # --- DODANE: linie ---
            if LINES_DIR and LINES_DIR.exists():
                for ldir in LINES_DIR.iterdir():
                    if ldir.is_dir():
                        for f in ldir.iterdir():
                            if f.is_file() and f.name.lower().startswith("linia_dane"):
                                st = f.stat()
                                sig.append((str(f), st.st_mtime, st.st_size))
        except Exception:
            # jednorazowe błędy I/O pomijamy – kolejny cykl spróbuje ponownie
            pass
        return tuple(sorted(sig))

    # --- cykl I/O: regeneruj obraz.txt/polaczenie.txt TYLKO gdy faktycznie zmieniły się źródła ---
    def _maybe_regenerate_obraz(self):
        try:
            sig = self._sources_signature()
            if sig != self._last_sources_sig:
                # zmiana w źródłach → przebuduj obraz.txt i polaczenie.txt
                try:
                    # gwarancja aktualnych danych
                    load_source_data()
                    write_obraz(list(SOURCE_CACHE.values()))

                    load_line_source_data()
                    write_polaczenie(list(LINE_SOURCE_CACHE.values()))
                except Exception:
                    return  # nie blokujemy GUI

                self._last_sources_sig = sig
                try:
                    self._last_obraz_mtime = OBRAZ_PATH.stat().st_mtime
                except Exception:
                    self._last_obraz_mtime = None
                try:
                    self._last_polaczenie_mtime = POLACZENIE_PATH.stat().st_mtime
                except Exception:
                    self._last_polaczenie_mtime = None

                self._dirty_display = True
        except Exception:
            pass

    # --- cykl GUI: szybki repaint bez ciężkiego I/O ---
    def refresh(self):
        if getattr(self, 'dragging', False):
            return

        # jeśli obraz.txt/polaczenie.txt podmieniony przez inny proces – zaznacz brudny
        try:
            mtime_obraz = OBRAZ_PATH.stat().st_mtime
        except Exception:
            mtime_obraz = None
        try:
            mtime_pol = POLACZENIE_PATH.stat().st_mtime
        except Exception:
            mtime_pol = None

        if mtime_obraz != self._last_obraz_mtime or mtime_pol != self._last_polaczenie_mtime:
            self._last_obraz_mtime = mtime_obraz
            self._last_polaczenie_mtime = mtime_pol
            self._dirty_display = True

        if not self._dirty_display:
            return

        self._render_scene()
        self._dirty_display = False

    # --- render: tylko rysowanie — ZERO ciężkiego I/O ---
    def _render_scene(self):
        prev_transform = QTransform(self.view.transform())
        self.scene.clear()

        # === LINIE ===
        try:
            line_display = load_line_display_data()
            self._build_lines_for_display(line_display)
        except:
            pass

        # === OBIEKTY ===
        try:
            display_data_list = load_display_data()
            self._build_items_for_display(display_data_list)
        except:
            pass

        # === restore zoom/pos ===
        try:
            self.view.setTransform(prev_transform, combine=False)
        except:
            pass

    # --- nowa/uzupełniona metoda: buduje elementy sceny z listy danych (IKONY) ---
    def _build_items_for_display(self, display_data_list):
        if not display_data_list:
            return

        for data in display_data_list:
            try:
                x = float(data.get('x', 0))
                y = float(data.get('y', 0))

                # priorytet: lokalna ikona.png z folderu obiektu
                agent_folder = data.get("agent_folder", "")
                local_icon = None

                if agent_folder:
                    cand = OBJECTS_DIR / agent_folder / "ikona.png"
                    if cand.exists():
                        local_icon = QPixmap(str(cand))

                # jak lokalna jest OK → użyj
                if local_icon and not local_icon.isNull():
                    pix = local_icon
                else:
                    # fallback → nazwa z obraz.txt / mapa_dane
                    ikona = (data.get('ikona') or '').strip()
                    pix = self._load_icon_pixmap(ikona)

                scale = float(str(data.get('rozmiar', '1')).replace(',', '.')) or 1.0

                # tworzymy MapItem
                item = MapItem(
                    pix,
                    data,
                    sensor_dir=getattr(self.view, '_sensor_dir', HERE / 'sensory'),
                    sensor_lock=getattr(self.view, '_sensor_lock', threading.Lock()),
                    sensor_write_fn=getattr(self.view, '_sensor_write', lambda *a, **k: None),
                    base_dir=BASE_DIR,
                    objects_dir=OBJECTS_DIR,
                )

                item.setScale(scale)
                w, h = pix.width() * scale, pix.height() * scale
                item.setPos(x - w / 2.0, y - h / 2.0)
                self.scene.addItem(item)

            except Exception:
                continue

    # --- NOWE: budowanie elementów sceny dla linii (LineItem) ---
    def _build_lines_for_display(self, line_display):
        if not line_display:
            return
        for d in line_display:
            try:
                item = LineItem(d)
                # linie są pod ikonami
                item.setZValue(0)
                self.scene.addItem(item)
            except Exception:
                continue

    def _load_icon_pixmap(self, ikona: str, agent_folder: str = "") -> QPixmap:
        """
        1) Jeśli w obiekcie istnieje obiekty/<agent_folder>/ikona.png → użyj jej.
        2) W innym wypadku użyj standardowej logiki (szukanie w /ikony).
        """

        # --- 1) Priorytet: lokalna ikona w folderze obiektu ---
        if agent_folder:
            local_icon = OBJECTS_DIR / agent_folder / "ikona.png"
            if local_icon.exists():
                pm = QPixmap(str(local_icon))
                if not pm.isNull():
                    return pm

        # --- 2) Stara logika globalna ---
        candidates = []
        if ikona:
            p = ICONS_DIR / ikona
            candidates.extend([
                p,
                p.with_suffix('.png'),
                p.with_suffix('.jpg'),
                p.with_suffix('.jpeg'),
                p.with_suffix('.bmp'),
                ICONS_DIR / (ikona + '.png'),
            ])
        for c in candidates:
            if c.exists():
                pm = QPixmap(str(c))
                if not pm.isNull():
                    return pm

        # --- 3) Placeholder ---
        pm = QPixmap(40, 40)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        pen = QPen(Qt.black)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(4, 4, 32, 32)
        painter.end()
        return pm

MAIN_WINDOW_INSTANCE = None

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    try:
        window = MainWindow()
        MAIN_WINDOW_INSTANCE = window

        # 🔇 wyłącz suwaki (nie rusza pan/zoom)
        window.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        window.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 🔥 start w fullscreen
        window.showFullScreen()

        # F11 ↔ fullscreen/okno
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        def toggle_fullscreen():
            window.showNormal() if window.isFullScreen() else window.showFullScreen()
        QShortcut(QKeySequence("F11"), window, toggle_fullscreen)

        # Esc → wyjście z fullscreen
        def handle_escape(event):
            if event.key() == Qt.Key_Escape and window.isFullScreen():
                window.showNormal()
            else:
                QMainWindow.keyPressEvent(window, event)
        window.keyPressEvent = handle_escape

        sys.exit(app.exec_())
    except Exception as e:
        log.error(f"Fatal: {e}")
        raise





