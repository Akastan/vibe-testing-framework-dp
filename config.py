"""
Centrální konfigurace frameworku.
Všechny konstanty a cesty na jednom místě.
"""
import os

# === CESTY ===
INPUTS_DIR = "inputs"
OUTPUTS_DIR = "outputs"
RESULTS_DIR = "results"

OPENAPI_PATH = os.path.join(INPUTS_DIR, "openapi.yaml")
DOC_PATH = os.path.join(INPUTS_DIR, "documentation.md")

# === LLM ===
MAX_ITERATIONS = 5  # Max počet iterací feedback loopu

# === BASE URL testovaného API ===
API_BASE_URL = "https://petstore3.swagger.io/api/v3"

# === ÚROVNĚ KONTEXTU ===
# Mapování úrovní na popis (pro výpis a budoucí rozšíření)
CONTEXT_LEVELS = {
    "L0": "OpenAPI specifikace (black-box baseline)",
    "L1": "OpenAPI + byznys dokumentace (dokumentovaný black-box)",
    "L2": "L1 + zdrojový kód endpointů (základní white-box)",
    "L3": "L2 + databázové schéma (pokročilý white-box)",
    "L4": "L3 + existující testy (plný kontext)",
}