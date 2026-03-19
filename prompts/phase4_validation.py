"""
Fáze 4: Spuštění vygenerovaných testů.
Spustí API server, pustí testy, vrátí log.
Server běží napříč iteracemi – restartuje se jen když přestane odpovídat.

Podporuje dva režimy:
  - Lokální (default): spustí Python subprocess z .venv
  - Docker (docker: true v experiment.yaml): spustí docker compose up

Opravy:
  - Automatický /reset před každým pytest spuštěním
  - Retry při infrastrukturních chybách (DB locked, connection error)
  - Detekce opakující se chyby → nepředávat LLM jako feedback
"""
import os
import sys
import re
import time
import subprocess
import requests as req

OUTPUTS_DIR = "outputs"

# Globální reference na běžící servery (sdílené napříč iteracemi)
_managed_servers: dict[str, subprocess.Popen] = {}

# Pro Docker režim: sledujeme, které API běží přes Docker
_docker_servers: dict[str, dict] = {}

# Kolikrát opakovat pytest při infra chybě (DB locked, connection refused)
INFRA_RETRY_MAX = 2
INFRA_RETRY_DELAY = 5  # sekund


# ═══════════════════════════════════════════════════════════
#  Pomocné funkce – lokální režim (beze změny)
# ═══════════════════════════════════════════════════════════

def _resolve_python(api_cfg: dict) -> str:
    abs_api = os.path.abspath(api_cfg["source_dir"])
    candidates = [
        os.path.join(abs_api, ".venv", "Scripts", "python.exe"),
        os.path.join(abs_api, ".venv", "bin", "python"),
        os.path.join(abs_api, "venv", "Scripts", "python.exe"),
        os.path.join(abs_api, "venv", "bin", "python"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return sys.executable


def _is_server_running(base_url: str) -> bool:
    try:
        return req.get(f"{base_url}/health", timeout=2).status_code == 200
    except Exception:
        return False


def _start_server_local(api_cfg: dict) -> subprocess.Popen | None:
    """Spustí server lokálně přes Python subprocess."""
    python_exe = _resolve_python(api_cfg)
    abs_api = os.path.abspath(api_cfg["source_dir"])
    cmd = api_cfg["server_cmd"]
    wait = api_cfg.get("startup_wait", 3.0)

    print(f"    [Server] Spouštím lokálně: {python_exe} {' '.join(cmd)}")
    kwargs = dict(cwd=abs_api, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen([python_exe] + cmd, **kwargs)

    for _ in range(int(wait * 4)):
        if proc.poll() is not None:
            err = proc.stderr.read().decode(errors="replace")
            print(f"    [Server] ❌ Nespustil se: {err[:200]}")
            return None
        if _is_server_running(api_cfg["base_url"]):
            print(f"    [Server] ✅ Běží.")
            return proc
        time.sleep(0.5)

    print(f"    [Server] ❌ Timeout.")
    proc.kill()
    return None


def _stop_server_local(proc):
    """Zastaví lokální subprocess."""
    if proc and proc.poll() is None:
        if os.name == "nt":
            proc.kill()
        else:
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        print(f"    [Server] Zastaven (lokální).")


# ═══════════════════════════════════════════════════════════
#  Pomocné funkce – Docker režim
# ═══════════════════════════════════════════════════════════

def _docker_compose_cmd(api_cfg: dict) -> list[str]:
    """Sestaví base příkaz pro docker compose."""
    compose_file = api_cfg.get("docker_compose_file", "docker-compose.yml")
    return ["docker", "compose", "-f", compose_file]


def _start_server_docker(api_cfg: dict) -> bool:
    """Spustí server přes docker compose up. Vrací True pokud se podařilo."""
    abs_api = os.path.abspath(api_cfg["source_dir"])
    base_cmd = _docker_compose_cmd(api_cfg)
    wait = api_cfg.get("startup_wait", 15.0)

    # Build + start (detached)
    print(f"    [Docker] Spouštím: docker compose up --build -d")
    result = subprocess.run(
        base_cmd + ["up", "--build", "-d"],
        cwd=abs_api,
        capture_output=True, text=True, timeout=300,
        encoding="utf-8", errors="replace",
    )

    if result.returncode != 0:
        print(f"    [Docker] ❌ docker compose up selhalo:")
        print(f"    {result.stderr[:300]}")
        return False

    # Čekej na health check
    print(f"    [Docker] Čekám na server (max {wait}s)...")
    for _ in range(int(wait * 2)):
        if _is_server_running(api_cfg["base_url"]):
            print(f"    [Docker] ✅ Server běží.")
            return True
        time.sleep(0.5)

    print(f"    [Docker] ❌ Timeout – server neodpovídá.")
    # Zobraz logy pro debug
    logs = subprocess.run(
        base_cmd + ["logs", "--tail", "30"],
        cwd=abs_api, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    print(f"    [Docker] Logy:\n{logs.stdout[-500:]}")
    return False


def _stop_server_docker(api_cfg: dict):
    """Zastaví Docker kontejner(y)."""
    abs_api = os.path.abspath(api_cfg["source_dir"])
    base_cmd = _docker_compose_cmd(api_cfg)

    print(f"    [Docker] Zastavuji kontejner...")
    subprocess.run(
        base_cmd + ["down", "--volumes", "--remove-orphans"],
        cwd=abs_api,
        capture_output=True, text=True, timeout=60,
        encoding="utf-8", errors="replace",
    )
    print(f"    [Docker] ✅ Zastaven.")


def _restart_server_docker(api_cfg: dict) -> bool:
    """Restartuje Docker kontejner (čistý stav – nová DB)."""
    abs_api = os.path.abspath(api_cfg["source_dir"])
    base_cmd = _docker_compose_cmd(api_cfg)
    wait = api_cfg.get("startup_wait", 15.0)

    print(f"    [Docker] Restartuji kontejner...")
    subprocess.run(
        base_cmd + ["down", "--volumes"],
        cwd=abs_api, capture_output=True, text=True, timeout=60,
        encoding="utf-8", errors="replace",
    )
    time.sleep(1)
    return _start_server_docker(api_cfg)


def _is_docker_mode(api_cfg: dict) -> bool:
    """Zjistí, zda API používá Docker režim."""
    return api_cfg.get("docker", False)


# ═══════════════════════════════════════════════════════════
#  Společné funkce (obě režimy)
# ═══════════════════════════════════════════════════════════

def _start_server(api_cfg: dict) -> subprocess.Popen | None:
    """Spustí server ve správném režimu. Pro Docker vrací dummy Popen-like objekt."""
    if _is_docker_mode(api_cfg):
        success = _start_server_docker(api_cfg)
        if success:
            # Uložíme si info že Docker běží
            _docker_servers[api_cfg["base_url"]] = api_cfg
            # Vrátíme None – Docker se neřídí přes Popen
            # ale musíme signalizovat úspěch jinak
            return "DOCKER_RUNNING"  # sentinel hodnota
        return None
    else:
        return _start_server_local(api_cfg)


def stop_managed_server(api_cfg: dict):
    """Zastaví server pro dané API. Volej po dokončení všech úrovní."""
    key = api_cfg["base_url"]

    if _is_docker_mode(api_cfg):
        if key in _docker_servers:
            _stop_server_docker(api_cfg)
            del _docker_servers[key]
    else:
        proc = _managed_servers.pop(key, None)
        if proc:
            _stop_server_local(proc)


def _reset_database(base_url: str) -> bool:
    """Zavolá /reset endpoint a počká na potvrzení."""
    try:
        r = req.post(f"{base_url}/reset", timeout=10)
        if r.status_code == 200:
            time.sleep(0.5)
            return True
        print(f"    [Reset] ⚠️ Status {r.status_code}: {r.text[:100]}")
        return False
    except Exception as e:
        print(f"    [Reset] ❌ Chyba: {e}")
        return False


# ── Detekce infrastrukturních chyb ──────────────────────

INFRA_ERROR_PATTERNS = [
    r"database is locked",
    r"OperationalError.*locked",
    r"sqlite3\.OperationalError",
    r"ConnectionError",
    r"ConnectionRefusedError",
    r"Connection refused",
    r"Read timed out",
    r"RemoteDisconnected",
    r"BrokenPipeError",
]

_infra_regex = re.compile("|".join(INFRA_ERROR_PATTERNS), re.IGNORECASE)


def _detect_infra_errors(pytest_output: str) -> tuple[bool, str | None]:
    failed_blocks = re.findall(
        r'FAILED.*?(?=\nFAILED|\n={3,}|\Z)', pytest_output, re.DOTALL
    )
    if not failed_blocks:
        return False, None
    match = _infra_regex.search(pytest_output)
    if not match:
        return False, None
    return True, match.group(0)


def _detect_single_root_cause(pytest_output: str) -> tuple[bool, str | None]:
    error_lines = re.findall(r'E\s+(.+)$', pytest_output, re.MULTILINE)
    if len(error_lines) < 2:
        return False, None

    def normalize(line):
        line = re.sub(r'\d+', 'N', line)
        line = re.sub(r'["\'].*?["\']', 'STR', line)
        return line.strip()

    normalized = [normalize(l) for l in error_lines]
    unique = set(normalized)
    most_common = max(unique, key=lambda x: normalized.count(x))
    ratio = normalized.count(most_common) / len(normalized)

    if ratio >= 0.8:
        idx = normalized.index(most_common)
        return True, error_lines[idx]
    return False, None


def _run_pytest(file_path: str) -> tuple[int, str]:
    result = subprocess.run(
        [
            "pytest", file_path, "-v", "--tb=short", "--disable-warnings",
            "--timeout=30",
            "--timeout-method=thread",
        ],
        capture_output=True, text=True, timeout=900,
    )
    return result.returncode, result.stdout + "\n" + result.stderr


# ═══════════════════════════════════════════════════════════
#  Hlavní funkce
# ═══════════════════════════════════════════════════════════

def run_tests_and_validate(
    test_code: str,
    output_filename: str,
    api_cfg: dict,
    iteration: int = 0,
) -> tuple[bool, str]:
    """Uloží kód, zajistí server, resetuje DB, spustí pytest, vrátí (success, log)."""
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    file_path = os.path.join(OUTPUTS_DIR, output_filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(test_code)

    base_url = api_cfg["base_url"]
    key = base_url
    is_docker = _is_docker_mode(api_cfg)

    # ── Zajistit běžící server ───────────────────────────
    if not _is_server_running(base_url):
        if is_docker:
            # Docker: restart kontejneru
            if key in _docker_servers:
                print(f"    [Docker] ⚠️ Server přestal odpovídat, restartuji...")
                if not _restart_server_docker(api_cfg):
                    return False, "SERVER_ERROR: Docker restart selhal.\n"
            else:
                if not _start_server_docker(api_cfg):
                    return False, "SERVER_ERROR: Nepodařilo se spustit Docker kontejner.\n"
                _docker_servers[key] = api_cfg
        else:
            # Lokální: restart subprocess
            old_proc = _managed_servers.pop(key, None)
            if old_proc and old_proc != "DOCKER_RUNNING":
                print(f"    [Server] ⚠️ Server přestal odpovídat, restartuji...")
                _stop_server_local(old_proc)
                time.sleep(2)

            proc = _start_server_local(api_cfg)
            if proc is None:
                return False, "SERVER_ERROR: Nepodařilo se spustit API server.\n"
            _managed_servers[key] = proc

    # ── Reset databáze před každým spuštěním testů ───────
    print(f"    [Reset] Čistím databázi...")
    if not _reset_database(base_url):
        print(f"    [Reset] ⚠️ Reset selhal, zkouším pokračovat...")

    # ── Spuštění pytest s retry při infra chybách ────────
    last_log = ""
    log_path = file_path.replace(".py", "_log.txt")

    # Append mode – ale první volání v tomto runu vyčistí soubor
    # (soubor se maže jen pokud ještě neexistuje iterace v tomto runu)
    if not hasattr(run_tests_and_validate, "_active_logs"):
        run_tests_and_validate._active_logs = set()
    if log_path not in run_tests_and_validate._active_logs:
        # První iterace tohoto runu → vyčistit předchozí data
        with open(log_path, "w", encoding="utf-8") as lf:
            lf.write(f"# Log pro: {output_filename}\n")
            lf.write(f"# Čas spuštění: {__import__('datetime').datetime.now().isoformat()}\n\n")
        run_tests_and_validate._active_logs.add(log_path)

    # ── Spuštění pytest s retry při infra chybách ────────
    last_log = ""
    for attempt in range(1, INFRA_RETRY_MAX + 1):
        try:
            returncode, full_log = _run_pytest(file_path)
            last_log = full_log

            # Připojit log této iterace (append)
            with open(log_path, "a", encoding="utf-8") as lf:
                lf.write(f"\n{'═' * 60}\n")
                lf.write(f"══ ITERACE {iteration} | pytest returncode={returncode}\n")
                lf.write(f"{'═' * 60}\n\n")
                lf.write(full_log)
                lf.write("\n")

            # Stručný výpis
            for line in full_log.strip().split("\n"):
                if any(k in line for k in ["passed", "failed", "FAILED", "ERROR"]):
                    print(f"    {line.strip()}")

            if returncode == 0:
                return True, full_log

            # Kontrola: je to infra chyba?
            is_infra, pattern = _detect_infra_errors(full_log)
            if is_infra and attempt < INFRA_RETRY_MAX:
                print(f"    ⚠️ Infra chyba detekována ({pattern})")
                print(f"    🔄 Retry {attempt}/{INFRA_RETRY_MAX} za {INFRA_RETRY_DELAY}s...")

                if is_docker:
                    _restart_server_docker(api_cfg)
                else:
                    old_proc = _managed_servers.pop(key, None)
                    if old_proc and old_proc != "DOCKER_RUNNING":
                        _stop_server_local(old_proc)
                        time.sleep(2)
                    proc = _start_server_local(api_cfg)
                    if proc:
                        _managed_servers[key] = proc

                time.sleep(INFRA_RETRY_DELAY)
                _reset_database(base_url)
                continue

            # Kontrola: mají všechny selhané testy stejnou root cause?
            is_single, root_msg = _detect_single_root_cause(full_log)
            if is_single:
                print(f"    ⚠️ Všechny chyby mají stejnou příčinu: {root_msg[:120]}")

                if _infra_regex.search(root_msg or ""):
                    if attempt < INFRA_RETRY_MAX:
                        print(f"    🔄 Retry (single root cause = infra)...")
                        _reset_database(base_url)
                        time.sleep(INFRA_RETRY_DELAY)
                        continue

                hint = (
                    f"\n\n=== FRAMEWORK HINT ===\n"
                    f"Všech {full_log.count('FAILED')} selhání má stejnou root cause.\n"
                    f"Zkontroluj, zda testy správně vytvářejí svá vlastní data "
                    f"a nepoléhají na data z jiných testů.\n"
                    f"Každý test musí být self-contained.\n"
                )
                return False, full_log + hint

            return False, full_log

        except subprocess.TimeoutExpired:
            last_log = "TIMEOUT: pytest překročil 600s limit.\n"
            print(f"    ❌ {last_log.strip()}")
            if attempt < INFRA_RETRY_MAX:
                print(f"    🔄 Retry po timeout...")
                _reset_database(base_url)
                time.sleep(INFRA_RETRY_DELAY)
                continue
            return False, last_log

    return False, last_log