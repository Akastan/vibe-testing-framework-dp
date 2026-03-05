import os
import subprocess


def run_tests_and_validate(test_code: str, output_filename: str = "test_generated.py") -> tuple[bool, str]:
    """
    Uloží vygenerovaný kód do souboru a spustí pytest v izolovaném subprocessu.
    Vrací tuple: (Úspěch - bool, Výstup z terminálu - str)
    """
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, output_filename)

    # Uložení kódu
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(test_code)

    print(f"Testovací kód uložen do {file_path}. Spouštím pytest...")

    # Spuštění testů přes příkazovou řádku
    result = subprocess.run(
        ["pytest", file_path, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )

    # pytest vrací returncode 0 pokud vše prošlo, 1 pokud něco selhalo
    if result.returncode == 0:
        return True, result.stdout
    else:
        # Spojíme standardní výstup a chybový výstup do jednoho logu pro LLM
        error_log = result.stdout + "\n" + result.stderr
        return False, error_log