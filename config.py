"""
Konfigurace pro manuální skripty (coverage, mutation, run_metrics_only).
Hlavní experiment se řídí souborem experiment.yaml.
"""
import os

OUTPUTS_DIR = "outputs"
RESULTS_DIR = "results"
INPUTS_DIR = "inputs"
OPENAPI_PATH = os.path.join(INPUTS_DIR, "openapi.yaml")

# Pro manuální skripty – defaultní API
API_SOURCE_DIR = os.path.join("..", "bookstore-api")
if os.name == "nt":
    API_PYTHON = os.path.join(API_SOURCE_DIR, ".venv", "Scripts", "python.exe")
else:
    API_PYTHON = os.path.join(API_SOURCE_DIR, ".venv", "bin", "python")