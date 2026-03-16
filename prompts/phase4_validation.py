"""
Fáze 4: Spuštění vygenerovaných testů.
Spustí API server, pustí testy, zastaví server, vrátí log.
"""
import os
import sys
import time
import subprocess
import requests as req

OUTPUTS_DIR = "outputs"


def _resolve_python(api_cfg: dict) -> str:
    """Najde Python executable pro API server."""
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


def _start_server(api_cfg: dict) -> subprocess.Popen | None:
    python_exe = _resolve_python(api_cfg)
    abs_api = os.path.abspath(api_cfg["source_dir"])
    cmd = api_cfg["server_cmd"]
    wait = api_cfg.get("startup_wait", 3.0)

    print(f"    [Server] Spouštím: {python_exe} {' '.join(cmd)}")
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


def _stop_server(proc):
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
        print(f"    [Server] Zastaven.")


def run_tests_and_validate(
    test_code: str,
    output_filename: str,
    api_cfg: dict,
) -> tuple[bool, str]:
    """Uloží kód, spustí server, spustí pytest, vrátí (success, log)."""
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    file_path = os.path.join(OUTPUTS_DIR, output_filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(test_code)

    # Server
    server_proc = None
    if not _is_server_running(api_cfg["base_url"]):
        server_proc = _start_server(api_cfg)
        if server_proc is None:
            return False, "SERVER_ERROR: Nepodařilo se spustit API server.\n"

    try:
        result = subprocess.run(
            ["pytest", file_path, "-v", "--tb=short", "--disable-warnings"],
            capture_output=True, text=True, timeout=600,
        )
        full_log = result.stdout + "\n" + result.stderr

        # Uložit log
        log_path = file_path.replace(".py", "_log.txt")
        with open(log_path, "w", encoding="utf-8") as lf:
            lf.write(full_log)

        # Stručný výpis
        for line in full_log.strip().split("\n"):
            if any(k in line for k in ["passed", "failed", "FAILED", "ERROR"]):
                print(f"    {line.strip()}")

        return (result.returncode == 0), full_log

    except subprocess.TimeoutExpired:
        msg = "TIMEOUT: pytest překročil 600s limit.\n"
        return False, msg

    finally:
        if server_proc:
            _stop_server(server_proc)