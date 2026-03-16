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
SOURCE_CODE_PATH = os.path.join(INPUTS_DIR, "source_code.py")
DB_SCHEMA_PATH = os.path.join(INPUTS_DIR, "db_schema.sql")
EXISTING_TESTS_PATH = os.path.join(INPUTS_DIR, "existing_tests.py")

# === LLM ===
MAX_ITERATIONS = 5  # Max počet iterací feedback loopu

# === BASE URL testovaného API ===
API_BASE_URL = "http://localhost:8000"

# === ÚROVNĚ KONTEXTU ===
CONTEXT_LEVELS = {
    "L0": "OpenAPI specifikace (black-box baseline)",
    "L1": "OpenAPI + byznys dokumentace (dokumentovaný black-box)",
    "L2": "L1 + zdrojový kód endpointů (základní white-box)",
    "L3": "L2 + databázové schéma (pokročilý white-box)",
    "L4": "L3 + existující testy (plný kontext)",
}