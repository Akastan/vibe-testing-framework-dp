import json
import os
import glob
from collections import defaultdict

# =====================================================================
# NASTAVENÍ SLOŽKY
# =====================================================================
COVERAGE_DIR = "outputs_v12_gemini/coverage_results"
OUTPUT_MD = "all_runs_detailed_summary.md"


# =====================================================================

def process_all_runs():
    # Najde všechny odpovídající JSON soubory ve složce coverage_results
    file_pattern = os.path.join(COVERAGE_DIR, "coverage_*__L*__run*.json")
    json_files = glob.glob(file_pattern)

    if not json_files:
        print(f"❌ Nebyly nalezeny žádné soubory ve složce '{COVERAGE_DIR}'.")
        return

    print(f"✅ Nalezeno {len(json_files)} coverage souborů. Zpracovávám...")

    results = []
    level_overall_stats = defaultdict(list)
    level_file_stats = defaultdict(lambda: defaultdict(list))
    all_files_set = set()

    for file_path in json_files:
        filename = os.path.basename(file_path)

        # Extrakce úrovně (L0-L4) a runu
        parts = filename.split('__')
        if len(parts) >= 3:
            level = parts[1]
            run_str = parts[2].replace('.json', '')
        else:
            level = "N/A"
            run_str = "N/A"

        # Načtení dat z JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        totals = data.get("totals", {})
        pct_covered = totals.get("percent_covered", 0.0)

        # Zpracování jednotlivých souborů
        files = data.get("files", {})
        file_pcts = {}
        for f_name, f_data in files.items():
            safe_name = f_name.replace('\\', '/')
            f_pct = f_data.get("percent_covered", 0.0)

            file_pcts[safe_name] = f_pct
            all_files_set.add(safe_name)  # Uložení do množiny všech známých souborů
            level_file_stats[level][safe_name].append(f_pct)  # Uložení pro průměrování

        # Uložení runu pro celkovou tabulku
        results.append({
            "filename": filename,
            "level": level,
            "run": run_str,
            "overall_pct": pct_covered,
            "files": file_pcts
        })

        # Uložení celkového pokrytí pro výpočet průměru
        level_overall_stats[level].append(pct_covered)

    # Seřazení runů a souborů pro konzistentní zobrazení v tabulce
    results = sorted(results, key=lambda x: (x['level'], x['run']))
    sorted_files = sorted(list(all_files_set))

    # ---------------------------------------------------------
    # TVORBA MARKDOWNU
    # ---------------------------------------------------------
    md_content = [
        "# 📊 Detailní report všech Coverage Runů (včetně souborů)",
        f"Zpracováno **{len(json_files)} běhů** ze složky `{COVERAGE_DIR}`.\n",
        "## 📈 Průměrné pokrytí podle úrovní (Levels)"
    ]

    # --- TABULKA 1: PRŮMĚRY ---
    # Hlavička
    header_avg = ["Úroveň", "Celkový průměr"] + [f"Průměr `{f}`" for f in sorted_files]
    md_content.append("| " + " | ".join(header_avg) + " |")
    md_content.append("|" + "|".join(["---"] * len(header_avg)) + "|")

    # Řádky pro průměry
    for level in sorted(level_overall_stats.keys()):
        # Výpočet celkového průměru
        ov_pcts = level_overall_stats[level]
        ov_avg = sum(ov_pcts) / len(ov_pcts) if ov_pcts else 0

        row = [f"**{level}**", f"**{ov_avg:.2f}%**"]

        # Výpočet průměru pro každý jednotlivý soubor
        for f_name in sorted_files:
            f_pcts = level_file_stats[level].get(f_name, [])
            f_avg = sum(f_pcts) / len(f_pcts) if f_pcts else 0
            row.append(f"{f_avg:.2f}%")

        md_content.append("| " + " | ".join(row) + " |")

    # --- TABULKA 2: VŠECHNY RUNY ---
    md_content.extend([
        "\n## 📋 Detailní přehled všech jednotlivých runů",
    ])

    # Hlavička
    header_det = ["Úroveň", "Run", "Celkově pokryto"] + [f"`{f}`" for f in sorted_files]
    md_content.append("| " + " | ".join(header_det) + " |")
    md_content.append("|" + "|".join(["---"] * len(header_det)) + "|")

    # Řádky pro všechny runy
    for r in results:
        row = [r['level'], r['run'], f"**{r['overall_pct']:.2f}%**"]

        for f_name in sorted_files:
            f_pct = r['files'].get(f_name, 0.0)
            row.append(f"{f_pct:.2f}%")

        md_content.append("| " + " | ".join(row) + " |")

    # Zápis hotového textu do souboru
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_content))

    print(f"🎉 Hotovo! Detailní report (včetně souborů) byl vygenerován do: {OUTPUT_MD}")


if __name__ == "__main__":
    process_all_runs()