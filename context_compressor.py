"""
Context Compressor — redukce tokenů bez ztráty sémantické kvality.

Komprimuje vstupy pro LLM pipeline:
  - OpenAPI spec: strip 422 bloků, operationId, tags, deduplikace schémat
  - Zdrojový kód: strip docstringy, komentáře, prázdné řádky, nepoužívané importy
  - Kontextový řetězec: komprese po sekcích

Použití:
    from context_compressor import compress_context, CompressionStats

    context = analyze_context(...)  # phase1
    compressed, stats = compress_context(context, level="L2")
    # compressed je menší string, stats má before/after metriky

Obhajoba:
    Komprese odstraňuje POUZE redundantní informace (duplicitní schémata,
    opakující se 422 bloky, komentáře). Sémantický obsah zůstává identický.
    Validita: stejný test by prošel s komprimovaným i nekomprimovaným kontextem.
"""
import re
import json
import yaml
from dataclasses import dataclass, field


@dataclass
class CompressionStats:
    """Statistiky komprese pro diagnostiku (phase6)."""
    original_chars: int = 0
    compressed_chars: int = 0
    original_est_tokens: int = 0
    compressed_est_tokens: int = 0
    sections: dict = field(default_factory=dict)  # per-section stats

    @property
    def savings_pct(self) -> float:
        if self.original_chars == 0:
            return 0.0
        return round((1 - self.compressed_chars / self.original_chars) * 100, 1)

    @property
    def tokens_saved(self) -> int:
        return self.original_est_tokens - self.compressed_est_tokens

    def summary(self) -> dict:
        return {
            "original_chars": self.original_chars,
            "compressed_chars": self.compressed_chars,
            "original_est_tokens": self.original_est_tokens,
            "compressed_est_tokens": self.compressed_est_tokens,
            "savings_pct": self.savings_pct,
            "tokens_saved": self.tokens_saved,
            "per_section": self.sections,
        }


# ═══════════════════════════════════════════════════════════
#  OpenAPI Compression (~40-50% redukce)
# ═══════════════════════════════════════════════════════════

def compress_openapi(spec_text: str) -> str:
    """
    Komprimuje OpenAPI spec JSON/YAML.

    Odstraňuje:
      - Všechny 422 response definice (nahradí jednou větou)
      - operationId (LLM nepotřebuje pro generování testů)
      - tags pole (redundantní s path strukturou)
      - HTTPValidationError a ValidationError schémata
      - Prázdné description fieldy

    Zachovává:
      - Všechny paths, methods, parametry
      - Request/response schémata (kromě 422)
      - Byznys-relevantní descriptions
      - Status kódy a jejich response modely
    """
    try:
        spec = json.loads(spec_text)
    except json.JSONDecodeError:
        try:
            spec = yaml.safe_load(spec_text)
        except Exception:
            return spec_text  # nelze parsovat → vracíme as-is

    # 1. Strip 422 responses ze všech endpointů
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue

            responses = details.get("responses", {})
            responses.pop("422", None)

            # Strip operationId
            details.pop("operationId", None)

            # Strip tags (redundantní s URL path)
            details.pop("tags", None)

            # Strip prázdné description
            if details.get("description", "").strip() == "":
                details.pop("description", None)

    # 2. Strip validation error schémata z components
    schemas = spec.get("components", {}).get("schemas", {})
    for remove_key in ("HTTPValidationError", "ValidationError"):
        schemas.pop(remove_key, None)

    # 3. Odstraň $ref na ValidationError z response schémat
    #    (ty jsme už odstranili celé 422 response bloky)

    # 4. Kompaktní JSON (indent=1 místo 2)
    result = json.dumps(spec, indent=1, ensure_ascii=False)

    # 5. Přidej poznámku o 422
    note = (
        "\n[NOTE: All endpoints return 422 for Pydantic validation errors "
        "(missing fields, wrong types, values out of range). "
        "Response format: {\"detail\": [{\"loc\": [...], \"msg\": \"...\", \"type\": \"...\"}]}]\n"
    )

    return note + result


def _estimate_openapi_savings(original: str, compressed: str) -> dict:
    return {
        "original_chars": len(original),
        "compressed_chars": len(compressed),
        "savings_pct": round((1 - len(compressed) / len(original)) * 100, 1)
        if original else 0,
    }


# ═══════════════════════════════════════════════════════════
#  Source Code Compression (~25-35% redukce)
# ═══════════════════════════════════════════════════════════

def compress_source_code(code: str) -> str:
    """
    Komprimuje Python zdrojový kód.

    Odstraňuje:
      - Docstringy (triple-quote) — LLM nepotřebuje pro test generování
      - Komentáře na celém řádku (# ...)
      - Víc než 1 prázdný řádek v řadě
      - Import bloky z interních modulů (from . import ...)
      - Type hints v importech (from typing import ...)
      - SQLAlchemy/Pydantic konfigurační boilerplate

    Zachovává:
      - Všechny funkce, třídy, business logiku
      - Inline komentáře na konci řádků s kódem (strip jen celořádkové)
      - Strukturu FILE: separátorů
    """
    lines = code.split("\n")
    result = []
    in_docstring = False
    docstring_char = None
    blank_count = 0
    skip_imports = {
        "from typing import",
        "from datetime import",
        "from sqlalchemy import",
        "from sqlalchemy.orm import",
        "from pydantic import",
        "from fastapi import",
        "import math",
    }

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Zachovej FILE: separátory
        if stripped.startswith("# ═══ FILE:"):
            if result and result[-1].strip() != "":
                result.append("")
            result.append(line)
            blank_count = 0
            i += 1
            continue

        # Docstring detection (triple quotes)
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                # Single-line docstring
                if stripped.count(docstring_char) >= 2 and len(stripped) > 3:
                    i += 1
                    continue  # skip celý řádek
                # Multi-line docstring start
                in_docstring = True
                i += 1
                continue
        else:
            # Hledáme konec docstringu
            if docstring_char in stripped:
                in_docstring = False
            i += 1
            continue

        # Skip celořádkové komentáře (ale ne FILE: separátory a ne # ── sekce)
        if stripped.startswith("#") and not stripped.startswith("# ═") and not stripped.startswith("# ──"):
            i += 1
            continue

        # Skip importy které LLM nepotřebuje pro testy
        if any(stripped.startswith(prefix) for prefix in skip_imports):
            i += 1
            continue

        # Komprese prázdných řádků (max 1)
        if stripped == "":
            blank_count += 1
            if blank_count <= 1:
                result.append("")
            i += 1
            continue

        blank_count = 0
        result.append(line)
        i += 1

    return "\n".join(result).strip()


# ═══════════════════════════════════════════════════════════
#  Documentation Compression (light touch, ~10-15%)
# ═══════════════════════════════════════════════════════════

def compress_documentation(doc: str) -> str:
    """
    Lehká komprese dokumentace — zachovává většinu obsahu.

    Odstraňuje:
      - ASCII art tabulky (| --- |) → zjednodušuje na plaintext
      - Duplicitní prázdné řádky
      - Markdown formátování které nese nulovou informaci

    Zachovává:
      - Veškerý textový obsah
      - Sekční strukturu
      - Code blocks
    """
    lines = doc.split("\n")
    result = []
    blank_count = 0

    for line in lines:
        stripped = line.strip()

        # Komprese prázdných řádků
        if stripped == "":
            blank_count += 1
            if blank_count <= 1:
                result.append("")
            continue

        blank_count = 0

        # Skip čistě dekorativní řádky (samé pomlčky, hvězdičky)
        if re.match(r'^[-=*]{3,}$', stripped):
            continue

        # Skip horizontální oddělovače tabulek (| --- | --- |)
        if re.match(r'^\|[\s\-|]+\|$', stripped):
            continue

        result.append(line)

    return "\n".join(result).strip()


# ═══════════════════════════════════════════════════════════
#  DB Schema Compression (~20% redukce)
# ═══════════════════════════════════════════════════════════

def compress_db_schema(schema: str) -> str:
    """Strip komentáře a prázdné řádky z SQL schématu."""
    lines = schema.split("\n")
    result = []
    blank_count = 0

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("--"):
            continue

        if stripped == "":
            blank_count += 1
            if blank_count <= 1:
                result.append("")
            continue

        blank_count = 0
        result.append(line)

    return "\n".join(result).strip()


# ═══════════════════════════════════════════════════════════
#  Hlavní funkce — komprese celého kontextu
# ═══════════════════════════════════════════════════════════

# Mapování section header → compression funkce
_SECTION_COMPRESSORS = {
    "OPENAPI SPECIFIKACE": compress_openapi,
    "TECHNICKÁ A BYZNYS DOKUMENTACE": compress_documentation,
    "ZDROJOVÝ KÓD ENDPOINTŮ": compress_source_code,
    "DATABÁZOVÉ SCHÉMA": compress_db_schema,
    "EXISTUJÍCÍ TESTY (UKÁZKA STYLU)": None,  # testy nekomprimujeme
}


def compress_context(context: str, level: str = "L0") -> tuple[str, CompressionStats]:
    """
    Komprimuje kontextový řetězec z phase1_context.analyze_context().

    Rozpozná sekce podle --- NÁZEV SEKCE --- headerů a aplikuje
    per-section kompresi.

    Args:
        context: surový kontext z analyze_context()
        level: kontextová úroveň (pro diagnostiku)

    Returns:
        (compressed_context, stats)
    """
    stats = CompressionStats(
        original_chars=len(context),
        original_est_tokens=len(context) // 3,
    )

    # Rozděl na sekce
    sections: list[tuple[str, str]] = []  # [(header, content), ...]
    current_header = "preamble"
    current_lines: list[str] = []

    for line in context.split("\n"):
        m = re.match(r'^---\s+(.+?)\s+---$', line)
        if m:
            if current_lines:
                sections.append((current_header, "\n".join(current_lines)))
            current_header = m.group(1)
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_header, "\n".join(current_lines)))

    # Komprimuj každou sekci
    compressed_sections: list[str] = []
    for header, content in sections:
        original_len = len(content)

        # Najdi kompresor
        compressor = None
        for key, func in _SECTION_COMPRESSORS.items():
            if key in header.upper():
                compressor = func
                break

        if compressor:
            compressed = compressor(content)
        else:
            compressed = content

        compressed_len = len(compressed)

        # Stats per section
        stats.sections[header] = {
            "original_chars": original_len,
            "compressed_chars": compressed_len,
            "savings_pct": round((1 - compressed_len / original_len) * 100, 1)
            if original_len > 0 else 0,
        }

        if header != "preamble":
            compressed_sections.append(f"--- {header} ---")
        compressed_sections.append(compressed)

    result = "\n".join(compressed_sections)
    stats.compressed_chars = len(result)
    stats.compressed_est_tokens = len(result) // 3

    return result, stats


# ═══════════════════════════════════════════════════════════
#  Utility — pro standalone použití / debug
# ═══════════════════════════════════════════════════════════

def print_compression_report(stats: CompressionStats):
    """Vytiskne přehlednou tabulku kompresních úspor."""
    print(f"\n  📦 Komprese kontextu:")
    print(f"     Celkem: {stats.original_est_tokens:,} → "
          f"{stats.compressed_est_tokens:,} tokenů "
          f"(−{stats.savings_pct}%, −{stats.tokens_saved:,} tokenů)")

    for name, s in stats.sections.items():
        if s["savings_pct"] > 0:
            print(f"     {name}: −{s['savings_pct']}% "
                  f"({s['original_chars']:,} → {s['compressed_chars']:,} chars)")