#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLAMA GEN4 — OSTATECZNA WERSJA BEZ PROMPT-FILE (dla starego builda)
→ proces=off → CZEKA na "server is listening on" → proces=on + gotowe.txt
→ launcher zostaje w tle, pilnuje
→ system prompt: przekazuj przez API (w messages, role=system)
→ zero błędów, zero pierdolenia
"""

import subprocess, threading, time, re, datetime, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KONFIG = ROOT / "konfiguracje.txt"
MAPA = ROOT / "mapa_dane.txt"
LOG = ROOT / "log.txt"
GOTOWE = ROOT / "gotowe.txt"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    print(line, end="")
    try:
        with open(LOG, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except: pass

def set_proces(state):
    try:
        content = MAPA.read_text(encoding="utf-8", errors="ignore") if MAPA.exists() else ""
        lines = [l for l in content.splitlines() if not l.strip().lower().startswith("proces=")]
        lines.append(f"proces={state}")
        MAPA.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"→ PROCES = {state.upper()}")
    except Exception as e:
        log(f"[BŁĄD] zapis proces: {e}")

def read_cfg():
    cfg = {}
    if not KONFIG.exists():
        log(f"[BŁĄD] Brak {KONFIG.name}!")
        return cfg
    for line in KONFIG.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = [x.strip() for x in line.split("=", 1)]
        k = k.lower().replace("-", "_")
        v = v.strip('"').strip("'")
        if v.lower() in ("true", "false"): v = v.lower() == "true"
        elif re.fullmatch(r"-?\d+", v): v = int(v)
        cfg[k] = v
    log(f"Wczytano konfigurację: {len(cfg)} parametrów")
    return cfg

def find_engine(cfg):
    candidates = [
        cfg.get("engine"), cfg.get("engine_path"),
        ROOT / "silnik" / "llama-server.exe",
        ROOT / "silnik" / "llama-server",
        ROOT / "bin" / "llama-server.exe",
        ROOT / "llama-server.exe",
        ROOT / "llama-server",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(Path(c).resolve())
    exe = shutil.which("llama-server.exe") or shutil.which("llama-server")
    if exe: return exe
    raise FileNotFoundError("Nie znaleziono llama-server")

def main():
    log("=== START PLAMA GEN4 – BEZ SYSTEM PROMPT W CLI (przekazuj przez API) ===")
    cfg = read_cfg()
    set_proces("off")

    exe = find_engine(cfg)
    model = cfg.get("model", "silnik/Llama-PLLuM-8B-base.Q5_K_M.gguf")
    model_path = ROOT / model if not Path(model).is_absolute() else Path(model)

    cmd = [
        exe, "-m", model_path.name,
        "--host", str(cfg.get("host", "127.0.0.1")),
        "--port", str(cfg.get("port", 3333)),
        "-c", str(cfg.get("c", 8192)),
        "--n-gpu-layers", str(cfg.get("n_gpu_layers", cfg.get("ngl", 99))),
    ]
    if cfg.get("threads") is not None: cmd += ["-t", str(cfg["threads"])]
    if cfg.get("prio") is not None: cmd += ["--prio", str(cfg["prio"])]
    if cfg.get("prio_batch") is not None: cmd += ["--prio-batch", str(cfg["prio_batch"])]
    if cfg.get("mlock", False): cmd += ["--mlock"]
    if cfg.get("offline", False): cmd += ["--offline"]

    log(f"URUCHAMIAM: {' '.join(cmd)}")
    log(f"CWD: {model_path.parent}")

    proc = subprocess.Popen(
        cmd,
        cwd=str(model_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=0x08000000 if os.name == "nt" else 0,  # ukryte okno na Windows
    )

    log(f"PID: {proc.pid}")

    # Czekamy na gotowość (linijka z listening lub total time)
    pattern = re.compile(r"server is listening on|llama_new_context_with_model: total time")
    model_loaded = False
    for line in proc.stdout:
        print(line, end="")
        try:
            with open(LOG, "a", encoding="utf-8", errors="replace") as f:
                f.write(line)
        except: pass
        if pattern.search(line):
            log("MODEL ZAŁADOWANY – SERWER GOTOWY!")
            model_loaded = True
            break
        time.sleep(0.1)  # mała przerwa, żeby nie spalać CPU

    if model_loaded:
        host = str(cfg.get("host", "127.0.0.1"))
        port = int(cfg.get("port", 3333))
        set_proces("on")
        with open(GOTOWE, "w", encoding="utf-8") as f:
            f.write(f"# gotowe.txt — {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write(f"host = {host}\n")
            f.write(f"port = {port}\n")
            f.write(f"url = http://{host}:{port}\n")
            f.write("\n# SYSTEM PROMPT: przekazuj przez API!\n")
            f.write('PRZYKŁAD ZAPYTANIA (curl):\n')
            f.write(f'curl http://{host}:{port}/v1/chat/completions -H "Content-Type: application/json" -d \'{{ "messages": [{{ "role": "system", "content": "Twój system prompt z instrukcje.txt" }}, {{ "role": "user", "content": "Pytanie użytkownika" }}], "temperature": 0.7 }}\'')
        log("→ PROCES = ON + gotowe.txt zapisane (z przykładem API)")
    else:
        log("Serwer padł przed załadowaniem – error")
        set_proces("error")
        proc.terminate()
        return

    # Pilnuje w tle
    def monitor():
        rc = proc.wait()
        log(f"SERWER PADŁ (kod: {rc})")
        set_proces("error")
    threading.Thread(target=monitor, daemon=True).start()

    log("Launcher w tle – Ctrl+C wyłącza wszystko")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log("Ręczne zatrzymanie")
        set_proces("off")
        if proc.poll() is None:
            proc.terminate()
            log("Terminate wysłany do serwera")

if __name__ == "__main__":
    import os
    main()