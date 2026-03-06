"""
Fáze 4: Automatické spuštění vygenerovaných testů a zachycení výstupu.
"""
import os
import subprocess

from config import OUTPUTS_DIR


def run_tests_and_validate(test_code: str, output_filename: str = "test_generated.py") -> tuple[bool, str]:
    """
    Uloží vygenerovaný kód do souboru a spustí pytest v subprocesu.

    Returns:
        (success: bool, output_log: str)
    """
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    file_path = os.path.join(OUTPUTS_DIR, output_filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(test_code)

    print(f"  Kód uložen do {file_path}. Spouštím pytest...")

    result = subprocess.run(
        ["pytest", file_path, "-v", "--tb=short", "--disable-warnings"],
        capture_output=True,
        text=True,
        timeout=120  # Timeout 2 minuty pro případ zacyklení
    )

    full_log = result.stdout + "\n" + result.stderr

    if result.returncode == 0:
        return True, full_log
    else:
        return False, full_log