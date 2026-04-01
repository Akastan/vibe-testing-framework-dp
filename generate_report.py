import os
import json
import glob
from collections import defaultdict

# --- KONFIGURACE ---
RESULTS_DIR = "./results"  # Složka, kde máš vygenerované JSONy z runů
OUTPUT_FILE = "last_run_auto.md"


def load_and_aggregate_data(results_dir):
    """Načte JSONy, uloží data pro jednotlivé runy a spočítá průměry odděleně pro každé LLM."""
    files = glob.glob(os.path.join(results_dir, "*.json"))

    # run_data[llm_name][run_id][level] = {metriky...}
    run_data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    # stats pro průměrování: stats[llm_name][level][metric] = [val1, val2, val3]
    stats = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    # Množina všech API pro hlavičku reportu
    api_names = set()

    for f in files:
        print(f"Zpracovávám soubor: {f}")
        with open(f, "r", encoding="utf-8") as file:
            try:
                data_list = json.load(file)
            except json.JSONDecodeError:
                print(f"  ❌ Nelze načíst {f} (špatný JSON formát).")
                continue

            for data in data_list:
                # Pokud run spadl na kritické chybě
                if "error" in data:
                    print(f"  ⚠️ Přeskakuji chybný run (Level {data.get('level')}): {data.get('error')}")
                    continue

                level = data.get("level", "L?")
                run_id = data.get("run_id", 0)
                llm_name = data.get("llm", "Neznámý")
                api_name = data.get("api", "Neznámé")

                api_names.add(api_name)

                metrics = data.get("metrics", {})

                # Extrakce hodnot
                extracted = {
                    "validity": metrics.get("test_validity", {}).get("validity_rate_pct", 0),
                    "stale": metrics.get("stale_tests", {}).get("stale_count", 0),
                    "iterations": data.get("iterations_used", 0),
                    "empty": metrics.get("empty_tests", {}).get("empty_count", 0),
                    "adherence": metrics.get("plan_adherence", {}).get("adherence_pct", 0),
                    # Opraven klíč na adherence_pct (z tvého JSONu)
                    "ep_cov": metrics.get("endpoint_coverage", {}).get("endpoint_coverage_pct", 0),
                    "ast_depth": metrics.get("assertion_depth", {}).get("assertion_depth", 0),
                    "avg_len": metrics.get("avg_test_length", {}).get("avg_lines", 0),
                    # Opraven klíč na avg_lines (z tvého JSONu)
                    "resp_val": metrics.get("response_validation", {}).get("response_validation_pct", 0)
                }

                # Uložíme pro konkrétní run pod daným LLM
                run_data[llm_name][run_id][level] = extracted

                # Uložíme pro celkový průměr pod daným LLM
                for k, v in extracted.items():
                    stats[llm_name][level][k].append(v)

    # Výpočet průměrů per LLM
    avg_stats = defaultdict(dict)
    for llm, levels_data in stats.items():
        for level, level_metrics in levels_data.items():
            avg_stats[llm][level] = {
                m: round(sum(vals) / len(vals), 2) if vals else 0
                for m, vals in level_metrics.items()
            }

    return run_data, avg_stats, list(api_names)


def generate_markdown(run_data, avg_stats, api_names):
    """Vloží data do Markdown šablony s rozpadem na modely, runy i průměry."""

    md = f"# Report z běhu experimentů\n\n"
    md += f"**Testovaná API:** {', '.join(api_names)}\n"
    md += f"**Parametry:** max 5 iterací (detailní parametry viz YAML)\n\n"
    md += "---\n\n"

    # Iterujeme přes každý nalezený LLM model
    for llm in sorted(run_data.keys()):
        md += f"# 🤖 Model: {llm}\n\n"

        runs = sorted(run_data[llm].keys())
        levels = sorted(avg_stats[llm].keys())

        # 1. SEKCE: JEDNOTLIVÉ RUNY (Pro konkrétní LLM)
        md += "## 🔍 Detailní výsledky jednotlivých běhů\n"
        md += "*Zde je vidět stabilita generování napříč jednotlivými pokusy.*\n\n"

        for run_id in runs:
            md += f"### Běh (Run) {run_id}\n"
            md += "| Level | Validity (%) | EP Cov (%) | Stale | Iterace | Empty | Ast Depth | Resp Val (%) | Adherence (%) |\n"
            md += "|-------|--------------|------------|-------|---------|-------|-----------|--------------|---------------|\n"
            for lvl in levels:
                d = run_data[llm][run_id].get(lvl, {})
                if not d:
                    continue  # Tento level v tomto runu chybí
                md += f"| **{lvl}** | {d.get('validity', '-')} | {d.get('ep_cov', '-')} | {d.get('stale', '-')} | {d.get('iterations', '-')} | {d.get('empty', '-')} | {d.get('ast_depth', '-')} | {d.get('resp_val', '-')} | {d.get('adherence', '-')} |\n"
            md += "\n"

        # 2. SEKCE: ZPRŮMĚROVANÁ DATA PRO RQs (Pro konkrétní LLM)
        md += "## 🎯 Výsledky pro Výzkumné otázky (Průměr ze všech runů)\n\n"

        md += "### RQ1: Vliv kontextu na Validity Rate\n"
        md += "| Level | Validity Rate (%) | Stale Testy (avg) | Iterace ke konvergenci (avg) | Empty Testy (avg) | Plan Adherence (%) |\n"
        md += "|-------|-------------------|-------------------|------------------------------|-------------------|--------------------|\n"
        for lvl in levels:
            d = avg_stats[llm][lvl]
            md += f"| **{lvl}** | {d['validity']} | {d['stale']} | {d['iterations']} | {d['empty']} | {d['adherence']} |\n"
        md += "\n"

        md += "### RQ2: Code & Endpoint Coverage\n"
        md += "| Level | EP Coverage (%) | Agreg. Assertion Depth | Avg Test Length (řádky) | Response Validation (%) |\n"
        md += "|-------|-----------------|------------------------|-------------------------|-------------------------|\n"
        for lvl in levels:
            d = avg_stats[llm][lvl]
            md += f"| **{lvl}** | {d['ep_cov']} | {d['ast_depth']} | {d['avg_len']} | {d['resp_val']} |\n"

        md += "\n---\n\n"

    md += "*Generováno skriptem z JSON výsledků.*\n"
    return md


if __name__ == "__main__":
    print(f"Hledám JSON výsledky ve složce: {RESULTS_DIR} ...")
    if not os.path.exists(RESULTS_DIR):
        print("Složka neexistuje! Změň cestu v RESULTS_DIR.")
    else:
        run_data, avg_stats, apis = load_and_aggregate_data(RESULTS_DIR)
        if not avg_stats:
            print("Nenašel jsem žádná platná data k agregaci.")
        else:
            report_content = generate_markdown(run_data, avg_stats, apis)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(report_content)

            print(f"\n✅ Hotovo! Report uložen do: {OUTPUT_FILE}")
            print(f"Zpracované modely: {', '.join(run_data.keys())}")