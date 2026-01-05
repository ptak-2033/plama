import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QGroupBox, QRadioButton, QButtonGroup
)

# 📂 Ścieżka do folderu tekst_dane
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEKST_DANE = BASE_DIR /"tekst_dane"

FILES = {
    "generalne": {
        "path": TEKST_DANE / "generalne.txt",
        "opcje": ["obiekty", "linie", "każdy", "brak"]
    },
    "linie": {
        "path": TEKST_DANE / "linie.txt",
        "opcje": ["id", "nazwa", "brak"]
    },
    "obiekty": {
        "path": TEKST_DANE / "obiekty.txt",
        "opcje": ["id", "nazwa", "brak"]
    }
}


class TekstDaneGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PLAMA – tekst_dane")
        self.setFixedSize(260, 400)

        self.layout = QVBoxLayout(self)
        self.groups = {}   # sekcja -> (group, path)

        TEKST_DANE.mkdir(parents=True, exist_ok=True)

        for sekcja, cfg in FILES.items():
            self.dodaj_sekcje(sekcja, cfg)

    def dodaj_sekcje(self, nazwa, cfg):
        box = QGroupBox(nazwa.upper())
        vbox = QVBoxLayout(box)

        group = QButtonGroup(self)

        path = cfg["path"]
        if not path.exists():
            path.write_text("brak", encoding="utf-8")

        aktualna = path.read_text(encoding="utf-8").strip()

        for opcja in cfg["opcje"]:
            btn = QRadioButton(opcja)
            group.addButton(btn)
            vbox.addWidget(btn)

            if opcja == aktualna:
                btn.setChecked(True)

        group.buttonClicked.connect(self.zapisz_z_gui)

        self.groups[group] = path
        self.layout.addWidget(box)

    def zapisz_z_gui(self, button):
        for group, path in self.groups.items():
            if button in group.buttons():
                path.write_text(button.text(), encoding="utf-8")
                return


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = TekstDaneGUI()
    gui.show()
    sys.exit(app.exec_())
