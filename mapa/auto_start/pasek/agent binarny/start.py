#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLAMA GEN4 — AGENT (auto-endpoint: /run -> /v1/chat/completions)
- *.txt I/O
- konfiguracja.txt: serwer=<NAZWA> (fallback: url=http://...)
- ../<NAZWA>/gotowe.txt: host/port/url (MINI)
- brak gotowe.txt -> proces=lag (max 30 s)
- błąd połączenia -> proces=lag 10 s + 1 retry
- logi -> log.txt
"""

import json, os, sys, tempfile, time, urllib.request, urllib.error, datetime
from pathlib import Path

ROOT          = Path(__file__).resolve().parent
PATH_CFG      = ROOT / "konfiguracja.txt"
PATH_MAPA     = ROOT / "mapa_dane.txt"
PATH_INSTR    = ROOT / "instrukcje.txt"
PATH_WEJSCIE  = ROOT / "wejście.txt"
PATH_WYJSCIE  = ROOT / "wyjście.txt"
PATH_LOG      = ROOT / "log.txt"

TIMEOUT_SEC             = 60
WAIT_GOTOWE_TOTAL_S     = 30
RETRY_SLEEP_S           = 10
ACCEPTED_JSON_KEYS      = ("result", "output", "response")

# =============== LOGI ===============
def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        with open(PATH_LOG, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass
    print(line, end="")

# =============== UTILS ===============
def read_text(path: Path) -> str:
    try:
        if not path.exists(): return ""
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as e:
        log(f"[WARN] Nie mogę odczytać {path.name}: {e}")
        return ""

def atomic_write(path: Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
            f.write(data)
        os.replace(tmp, str(path))
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def set_proces(status: str):
    try:
        lines = read_text(PATH_MAPA).splitlines() if PATH_MAPA.exists() else []
        out, hit = [], False
        for line in lines:
            if line.strip().lower().startswith("proces="):
                out.append(f"proces={status}"); hit = True
            else:
                out.append(line)
        if not hit: out.append(f"proces={status}")
        atomic_write(PATH_MAPA, "\n".join(out) + ("\n" if out else ""))
        log(f"proces={status}")
    except Exception as e:
        log(f"[WARN] Nie mogę zapisać proces={status}: {e}")

# =============== KONFIG / GOTOWE ===============
def parse_konfiguracja() -> dict:
    cfg = {"serwer": None, "temp": 0.5, "max_token": 2048, "url": None}
    txt = read_text(PATH_CFG)
    for raw in txt.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        k, v = k.strip().lower(), v.strip()
        if k in ("serwer","server","srv"): cfg["serwer"] = v
        elif k == "url": cfg["url"] = v
        elif k in ("temp","temperature"):
            try: cfg["temp"] = float(v)
            except: pass
        elif k in ("max_token","maxtoken","max_tokens"):
            try: cfg["max_token"] = int(v)
            except: pass
    log(f"Wczytano konfigurację: {cfg}")
    return cfg

def parse_gotowe(folder_serwera: Path) -> dict:
    info = {"host": None, "port": None, "url": None}
    f = folder_serwera / "gotowe.txt"
    txt = read_text(f)
    for raw in txt.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("- ") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "host": info["host"] = v
        elif k == "port":
            try: info["port"] = int(v)
            except: pass
        elif k == "url": info["url"] = v
    if not info["url"] and info["host"] and info["port"]:
        info["url"] = f"http://{info['host']}:{info['port']}"
    log(f"gotowe.txt → {info}")
    return info

def resolve_url(cfg: dict) -> str:
    if cfg.get("serwer"):
        target = Path(__file__).resolve().parents[1] / cfg["serwer"]
        f_got = target / "gotowe.txt"
        t0 = time.time()
        while not f_got.exists() and (time.time() - t0) < WAIT_GOTOWE_TOTAL_S:
            set_proces("lag")
            log(f"Czekam na {f_got} …")
            time.sleep(1)
        if not f_got.exists():
            raise RuntimeError(f"Nie znaleziono {f_got} w czasie {WAIT_GOTOWE_TOTAL_S}s.")
        info = parse_gotowe(target)
        if not info.get("url"):
            if info.get("host") and info.get("port"):
                return f"http://{info['host']}:{info['port']}"
            raise RuntimeError("gotowe.txt nie zawiera url/host/port.")
        return info["url"]
    if cfg.get("url"):
        return cfg["url"]
    raise RuntimeError("Brak 'serwer=<NAZWA>' i brak 'url=' w konfiguracja.txt.")

# =============== HTTP HELPERS ===============
def http_post(url: str, payload: dict) -> (str, dict):
    """Zwraca (body_text, headers_dict) lub rzuca wyjątek HTTP/URL/timeout."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    log(f"POST → {url} (timeout={TIMEOUT_SEC}s, bytes={len(data)})")
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        log(f"HTTP {resp.status}, len={len(body)})")
        return body, dict(resp.headers)

def post_run(url_run: str, instructions: str, input_text: str, temp: float, max_token: int) -> str:
    payload = {"instructions": instructions, "input": input_text, "temp": temp, "max_token": max_token}
    body, _ = http_post(url_run, payload)
    # przyjmij czysty tekst albo JSON {result|output|response}
    try:
        j = json.loads(body)
        for k in ("result","output","response"):
            if k in j: return str(j[k])
        return body
    except json.JSONDecodeError:
        return body

def post_chat(base_url: str, instructions: str, input_text: str, temp: float, max_token: int) -> str:
    """OpenAI/llama.cpp compatible: POST {base}/v1/chat/completions"""
    url = base_url.rstrip("/") + "/v1/chat/completions"
    messages = []
    if instructions:
        messages.append({"role":"system","content":instructions})
    messages.append({"role":"user","content":input_text or ""})
    payload = {
        # wiele serwerów przyjmie brak modelu gdy jest 1 załadowany; jak nie, podają błąd 400 – przekażemy go w wyjściu.
        "messages": messages,
        "temperature": float(temp),
        "max_tokens": int(max_token),
        # "model": "default"  # odkomentuj jeśli Twój serwer tego wymaga
    }
    body, _ = http_post(url, payload)
    # standard OpenAI: choices[0].message.content
    try:
        j = json.loads(body)
        if isinstance(j, dict) and "choices" in j and j["choices"]:
            msg = j["choices"][0].get("message", {})
            content = msg.get("content", "")
            return content if content else body
        return body
    except json.JSONDecodeError:
        return body

# =============== RUN LOGIC (AUTO-ENDPOINT) ===============
def smart_call(raw_url: str, instructions: str, input_text: str, temp: float, max_token: int) -> str:
    """
    1) jeśli raw_url już kończy się /run → spróbuj /run; 404 => przełącz na /v1/chat/completions
    2) jeśli raw_url to root → najpierw /run, a przy 404 → /v1/chat/completions
    """
    # Bazowy root (bez trailing /run)
    base = raw_url
    if base.rstrip("/").endswith("/run"):
        base = base.rstrip("/")
        base = base[: -len("/run")]
    base = base.rstrip("/")

    # 1st try: /run
    try:
        url_run = base + "/run"
        return post_run(url_run, instructions, input_text, temp, max_token)
    except urllib.error.HTTPError as e:
        if getattr(e, "code", None) == 404:
            log("[AUTO] 404 na /run → próbuję /v1/chat/completions")
        else:
            log(f"[AUTO] Błąd na /run: {e} → spróbuję /v1/chat/completions")
    except (urllib.error.URLError, TimeoutError) as e:
        log(f"[AUTO] Sieć na /run: {e} → spróbuję /v1/chat/completions")

    # 2nd try: /v1/chat/completions
    return post_chat(base, instructions, input_text, temp, max_token)

def try_run_auto(raw_url: str, instructions: str, input_text: str, temp: float, max_token: int) -> str:
    """Auto-endpoint + 1 retry z lagiem przy problemach sieciowych."""
    try:
        return smart_call(raw_url, instructions, input_text, temp, max_token)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        log(f"[NET] {type(e).__name__}: {e} → lag {RETRY_SLEEP_S}s + retry")
        set_proces("lag")
        time.sleep(RETRY_SLEEP_S)
        return smart_call(raw_url, instructions, input_text, temp, max_token)

# =============== MAIN ===============
def clean_output(txt: str) -> str:
    """Czyści <|im_start|> / <|im_end|> i role, zostawia samą treść."""
    import re
    txt = re.sub(r"<\|im_start\|>.*?\n", "", txt)
    txt = re.sub(r"<\|im_end\|>", "", txt)
    txt = re.sub(r"\b(user|assistant)\b\s*", "", txt)
    return txt.strip()

def main():
    log("=== START AGENTA ===")
    set_proces("on")
    try:
        cfg = parse_konfiguracja()
        raw_url = resolve_url(cfg)
        log(f"Finalny URL (raw): {raw_url}")

        instr = read_text(PATH_INSTR)
        wej   = read_text(PATH_WEJSCIE)
        log(f"Długość instrukcji: {len(instr)} znaków, wejścia: {len(wej)} znaków")

        result = try_run_auto(raw_url, instr, wej, cfg.get("temp", 0.5), cfg.get("max_token", 2048))

        clean = clean_output(result if isinstance(result, str) else str(result))
        atomic_write(PATH_WYJSCIE, clean)
        log(f"Wynik zapisany → {PATH_WYJSCIE.name} ({len(clean)} znaków)")

        set_proces("off")
        log("=== KONIEC OK ===")
        return 0

    except Exception as e:
        msg = f"[AGENT ERROR] {type(e).__name__}: {e}"
        atomic_write(PATH_WYJSCIE, msg)
        log(msg)
        set_proces("error")
        log("=== KONIEC Z BŁĘDEM ===")
        return 1

if __name__ == "__main__":
    sys.exit(main())
