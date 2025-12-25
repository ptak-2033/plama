import tkinter as tk
import sys
import subprocess
from pathlib import Path

LIGHT_GREEN = "#a8ffb0"   # jasno zielony
BRIGHT_GREEN = "#00ff00"  # start
RED = "#ff3333"            # błąd
BG = "#000000"

class Launcher:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.title("Launcher")

        w, h = 320, 120
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.attributes("-topmost", True)

        self.label = tk.Label(
            self.root,
            text="Uruchamiam…",
            fg=LIGHT_GREEN,
            bg=BG,
            font=("Segoe UI", 18, "bold")
        )
        self.label.pack(expand=True, fill="both")

        self.root.after(200, self.try_launch)

    def try_launch(self):
        try:
            target = Path(__file__).resolve().parents[2] / "start.py"
            if not target.exists():
                self.fail("Brak pliku: start.py")
                return

            creationflags = 0
            if sys.platform.startswith("win"):
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

            subprocess.Popen(
                [sys.executable, str(target)],
                cwd=str(target.parent),
                creationflags=creationflags,
                close_fds=True,
                shell=False
            )

            self.label.config(text="START", fg=BRIGHT_GREEN)
            self.root.after(800, self.root.destroy)
        except Exception as e:
            self.fail(str(e))

    def fail(self, msg: str):
        self.label.config(text=f"BŁĄD\n{msg}", fg=RED)
        self.root.after(2500, self.root.destroy)

def main():
    root = tk.Tk()
    Launcher(root)
    root.mainloop()

if __name__ == "__main__":
    main()
