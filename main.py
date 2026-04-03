"""
Vibe Testing Framework – Experiment Runner (v2.2 — token tracking).

Změny oproti v2.1:
- TokenTracker per run — přesné měření tokenů z API response
- TrackingLLMWrapper — transparentní proxy, phase moduly beze změny
- token_usage + token_usage_slim ve výstupním JSON

Prerekvizita: llm_provider.py musí vracet (text, usage_dict) z generate_text().
Viz token_tracker.py pro extract_usage_* funkce per provider.
"""
import os
import json
import time
import yaml
from datetime import datetime
from dotenv import load_dotenv

from llm_provider import create_llm
from token_tracker import TokenTracker
from prompts.prompt_templates import PromptBuilder
from prompts.phase1_context import analyze_context
from prompts.phase2_planning import generate_test_plan
from prompts.phase3_generation import (
    generate_test_code, repair_failing_tests, validate_test_count,
    count_test_functions, StaleTracker,
)
from prompts.phase4_validation import run_tests_and_validate, stop_managed_server
from prompts.phase5_metrics import calculate_all_metrics, parse_test_validity_rate
from prompts.phase6_diagnostics import (
    collect_all_diagnostics, RepairTracker as DiagRepairTracker,
)

OUTPUTS_DIR = "outputs"
RESULTS_DIR = "results"

CONTEXT_LEVELS = {
    "L0": "OpenAPI specifikace",
    "L1": "OpenAPI + dokumentace",
    "L2": "L1 + zdrojový kód",
    "L3": "L2 + DB schéma",
    "L4": "L3 + existující testy",
}


# ─── Tracking wrapper ────────────────────────────────────
# Obalí LLM provider, zachytí (text, usage) a předá jen text.
# Phase moduly volají wrapper.generate_text(prompt) → str (beze změny).
# Wrapper interně zaznamenává tokeny do TokenTracker.
#
# PREREKVIZITA: LLM provider musí vracet tuple (text, usage_dict | None).
# Pokud vrací jen str (stará verze), wrapper funguje v degraded režimu
# (nezaznamenává tokeny, jen loguje warning).

class TrackingLLMWrapper:
    """Transparentní proxy nad LLM providerem s automatickým token trackingem."""

    def __init__(self, llm, tracker: TokenTracker):
        self._llm = llm
        self._tracker = tracker
        self._phase = "unknown"
        self._detail = ""
        self._warned = False

    def set_phase(self, phase: str, detail: str = ""):
        """Nastav aktuální fázi — volej před každým blokem LLM callů."""
        self._phase = phase
        self._detail = detail

    def generate_text(self, prompt: str) -> str:
        """Volá underlying LLM, zaznamenává usage, vrací jen text."""
        result = self._llm.generate_text(prompt)

        # Nový provider: vrací (text, usage_dict)
        if isinstance(result, tuple):
            text, usage = result
            self._tracker.record(self._phase, usage, detail=self._detail)
            return text

        # Starý provider: vrací jen str — degraded režim
        if not self._warned:
            print("  ⚠️ LLM provider nevrací usage data — token tracking nedostupný.")
            print("     Uprav generate_text() v llm_provider.py aby vracel (text, usage).")
            self._warned = True
        return result

    # Proxy: předej všechno ostatní na underlying LLM
    def __getattr__(self, name):
        return getattr(self._llm, name)


def load_experiment_config(path: str = "experiment.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _sanitize_tag(name: str) -> str:
    return name.replace(".", "_").replace(" ", "_")


def _temp_tag(temperature) -> str:
    """Vrátí tag pro temperature do názvu souboru. None → prázdný string."""
    if temperature is None:
        return ""
    return f"__t{str(temperature).replace('.', '_')}"


def run_pipeline(
    llm, llm_name: str, api_cfg: dict, level: str,
    run_id: int, test_count: int, max_iterations: int,
    temperature=None,
) -> dict:
    """Spustí jednu kombinaci: 1 LLM × 1 API × 1 Level × 1 Run (× 1 Temperature)."""
    api_name = api_cfg["name"]
    tag = f"{_sanitize_tag(llm_name)}__{api_name}__{level}__run{run_id}{_temp_tag(temperature)}"
    output_filename = f"test_generated_{tag}.py"
    plan_filename = f"test_plan_{tag}.json"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    inputs = api_cfg["inputs"]

    # ── Token tracker per run ───────────────────────────
    # model name pro pricing lookup
    model_name = getattr(llm, "model", llm_name)
    if isinstance(llm, TrackingLLMWrapper):
        model_name = getattr(llm._llm, "model", llm_name)
    tracker = TokenTracker(model=model_name)
    tracked_llm = TrackingLLMWrapper(llm, tracker)

    # ── Unified prompt builder (z api_cfg + level) ──────
    prompt_builder = PromptBuilder(api_cfg, level=level)

    temp_str = f" | temp={temperature}" if temperature is not None else ""
    print(f"\n{'=' * 65}")
    print(f"  {llm_name} | {api_name} | {level} | Běh {run_id}{temp_str}")
    print(f"{'=' * 65}")

    start_time = time.time()

    # ── FÁZE 1: Kontext ──────────────────────────────────
    context = analyze_context(
        openapi_path=inputs["openapi"],
        doc_path=inputs.get("documentation"),
        level=level,
        source_code_path=inputs.get("source_code"),
        db_schema_path=inputs.get("db_schema"),
        existing_tests_path=inputs.get("existing_tests"),
    )

    # ── FÁZE 2: Plánování ────────────────────────────────
    print(f"  [Fáze 2] Generování plánu ({test_count} testů)...")
    tracked_llm.set_phase("planning")
    test_plan = generate_test_plan(
        context, tracked_llm, prompt_builder=prompt_builder,
        test_count=test_count,
    )

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(os.path.join(OUTPUTS_DIR, plan_filename), "w", encoding="utf-8") as f:
        json.dump(test_plan, f, indent=2, ensure_ascii=False)

    plan_test_count = sum(
        len(ep.get("test_cases", []))
        for ep in test_plan.get("test_plan", [])
    )
    print(f"  Plán: {plan_test_count} testů")

    # ── FÁZE 3 + 4: Generování + Feedback loop ──────────
    print(f"  [Fáze 3+4] Generování kódu (max {max_iterations} iterací)...")
    tracked_llm.set_phase("generation")
    test_code = generate_test_code(
        test_plan, context, tracked_llm,
        prompt_builder=prompt_builder,
        base_url=api_cfg["base_url"],
    )

    actual_count = count_test_functions(test_code)
    if plan_test_count > 0:
        tracked_llm.set_phase("generation_fill")
        test_code = validate_test_count(
            test_code, plan_test_count, llm=tracked_llm,
            prompt_builder=prompt_builder,
            base_url=api_cfg["base_url"], context=context,
        )
        actual_count = count_test_functions(test_code)
    print(f"  Testů v kódu: {actual_count} (plán: {plan_test_count})")

    # Stale tracker per run
    stale_tracker = StaleTracker(threshold=2)
    # Diagnostický repair tracker
    diag_repair_tracker = DiagRepairTracker()

    iteration = 0
    success = False
    output_log = ""
    last_repair_type = None

    while iteration < max_iterations and not success:
        iteration += 1
        print(f"\n  --- Iterace {iteration}/{max_iterations} ---")

        success, output_log = run_tests_and_validate(
            test_code,
            output_filename=output_filename,
            api_cfg=api_cfg,
            iteration=iteration,
        )

        if success:
            print("  ✅ Všechny testy prošly!")
            diag_repair_tracker.record_iteration(iteration, output_log)
        elif iteration < max_iterations:
            print("  ❌ Testy selhaly. Opravuji...")
            diag_repair_tracker.record_iteration(iteration, output_log)
            tracked_llm.set_phase("repair", detail=f"iter{iteration}")
            test_code, repair_info = repair_failing_tests(
                test_code, output_log, context, tracked_llm,
                prompt_builder=prompt_builder,
                base_url=api_cfg["base_url"],
                stale_tracker=stale_tracker,
                previous_repair_type=last_repair_type,
            )
            last_repair_type = repair_info["repair_type"]
            diag_repair_tracker.annotate_last(
                repair_type=repair_info["repair_type"],
                repaired_count=repair_info["repaired_count"],
                stale_skipped=repair_info["stale_skipped"],
            )
        else:
            print(f"  ⚠️ Max iterací dosaženo.")
            diag_repair_tracker.record_iteration(iteration, output_log)

    elapsed = round(time.time() - start_time, 2)

    # ── FÁZE 5: Metriky ─────────────────────────────────
    tv = parse_test_validity_rate(output_log)
    metrics = calculate_all_metrics(
        file_path=output_path,
        pytest_output=output_log,
        openapi_path=inputs["openapi"],
        test_plan=test_plan,
    )

    # Přidej stale info do metrik
    metrics["stale_tests"] = {
        "stale_count": len(stale_tracker.get_stale()),
        "stale_names": stale_tracker.get_stale(),
    }

    ec = metrics["endpoint_coverage"]
    ad = metrics["assertion_depth"]
    rv = metrics["response_validation"]
    et = metrics["empty_tests"]
    st = metrics["stale_tests"]

    # ── Token usage summary ──────────────────────────────
    token_summary = tracker.summary()
    token_slim = tracker.summary_slim()

    print(f"\n  {'─' * 50}")
    print(f"  Validity:   {tv['validity_rate_pct']}% ({tv['tests_passed']}/{tv['total_executed']})")
    print(f"  Endpoint:   {ec['endpoint_coverage_pct']}% ({ec['covered_endpoints']}/{ec['total_api_endpoints']})")
    print(f"  Assert:     {ad['assertion_depth']} avg ({ad['total_assertions']} total)")
    print(f"  Body check: {rv['response_validation_pct']}% ({rv['tests_with_body_check']}/{rv['total_test_functions']})")
    print(f"  Status codes: {metrics['status_code_diversity']['diversity_count']} unique")
    print(f"  Empty tests: {et['empty_count']}")
    print(f"  Stale tests: {st['stale_count']}")
    print(f"  Čas:        {elapsed}s | Iterací: {iteration}")
    # Token info
    print(f"  Tokeny:     {token_slim['total_tokens']:,} total "
          f"({token_slim['prompt_tokens']:,} in / "
          f"{token_slim['completion_tokens']:,} out) "
          f"| {token_slim['total_calls']} calls")
    if token_slim["pricing_found"]:
        print(f"  Cena:       ${token_slim['cost_usd']:.4f}")
    else:
        print(f"  Cena:       N/A (model '{tracker.model}' není v pricing tabulce)")

    # ── FÁZE 6: Diagnostika ──────────────────────────
    plan_json_str = json.dumps(test_plan, indent=2, ensure_ascii=False)
    diagnostics = collect_all_diagnostics(
        context=context,
        test_plan=test_plan,
        code=test_code,
        pytest_log=output_log,
        openapi_path=inputs["openapi"],
        plan_json_str=plan_json_str,
        repair_tracker=diag_repair_tracker,
    )

    return {
        "timestamp": datetime.now().isoformat(),
        "llm": llm_name,
        "api": api_name,
        "level": level,
        "run_id": run_id,
        "temperature": temperature,
        "iterations_used": iteration,
        "all_tests_passed": success,
        "elapsed_seconds": elapsed,
        "plan_test_count": plan_test_count,
        "output_filename": output_filename,
        "plan_filename": plan_filename,
        "metrics": metrics,
        "diagnostics": diagnostics,
        "token_usage": token_summary,          # ← plný breakdown per phase
        "token_usage_slim": token_slim,         # ← pro rychlý přehled / agregace
    }


def main():
    load_dotenv()

    cfg = load_experiment_config()
    exp = cfg["experiment"]
    levels = exp["levels"]
    max_iter = exp["max_iterations"]
    runs = exp["runs_per_combination"]
    test_count = exp["test_count"]
    temperatures = exp.get("temperatures", [None])

    total = len(cfg["llms"]) * len(cfg["apis"]) * len(levels) * runs * len(temperatures)
    temp_info = f" × {len(temperatures)} temps" if temperatures != [None] else ""
    print(f"\n🔬 EXPERIMENT: {exp['name']}")
    print(f"   {len(cfg['llms'])} LLMs × {len(cfg['apis'])} APIs × {len(levels)} levels × {runs} runs{temp_info} = {total} běhů")
    print(f"   Max iterací: {max_iter} | Testů na plán: {test_count}")
    if temperatures != [None]:
        print(f"   Temperatures: {temperatures}")
    print()

    all_results = []
    done = 0

    # ── Agregované token stats přes celý experiment ──────
    total_tokens_all = 0
    total_cost_all = 0.0

    for llm_cfg in cfg["llms"]:
        api_key = os.environ.get(llm_cfg["api_key_env"])
        if not api_key:
            print(f"⚠️ {llm_cfg['api_key_env']} nenalezen, přeskakuji {llm_cfg['name']}")
            continue

        # Extra kwargs pro provider (base_url, max_tokens, num_ctx, verify_ssl)
        llm_extra = {}
        if "base_url_env" in llm_cfg:
            llm_extra["base_url"] = os.environ.get(llm_cfg["base_url_env"], "")
        for k in ("max_tokens", "num_ctx", "verify_ssl"):
            if k in llm_cfg:
                llm_extra[k] = llm_cfg[k]

        print(f"\n🤖 LLM: {llm_cfg['name']}")

        for api_cfg in cfg["apis"]:
            print(f"\n📦 API: {api_cfg['name']}")

            for level in levels:
                for temp in temperatures:
                    # Vytvoř LLM instanci s konkrétní teplotou
                    llm = create_llm(
                        llm_cfg["provider"], api_key, llm_cfg["model"],
                        temperature=temp, **llm_extra,
                    )

                    for run_id in range(1, runs + 1):
                        done += 1
                        print(f"\n[{done}/{total}] ", end="")

                        try:
                            result = run_pipeline(
                                llm=llm,
                                llm_name=llm_cfg["name"],
                                api_cfg=api_cfg,
                                level=level,
                                run_id=run_id,
                                test_count=test_count,
                                max_iterations=max_iter,
                                temperature=temp,
                            )
                            all_results.append(result)

                            # Agreguj token stats
                            slim = result.get("token_usage_slim", {})
                            total_tokens_all += slim.get("total_tokens", 0)
                            total_cost_all += slim.get("cost_usd", 0)

                        except Exception as e:
                            print(f"  ❌ CHYBA: {e}")
                            all_results.append({
                                "llm": llm_cfg["name"],
                                "api": api_cfg["name"],
                                "level": level,
                                "run_id": run_id,
                                "temperature": temp,
                                "error": str(e),
                            })

            stop_managed_server(api_cfg)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RESULTS_DIR, f"experiment_{exp['name']}_{timestamp}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n\n{'=' * 65}")
    print(f"  EXPERIMENT DOKONČEN | {len(all_results)} běhů | Výsledky: {path}")
    print(f"{'=' * 65}")

    ok = sum(1 for r in all_results if r.get("all_tests_passed"))
    err = sum(1 for r in all_results if "error" in r)
    print(f"  ✅ Passed: {ok} | ❌ Failed: {len(all_results) - ok - err} | 💥 Error: {err}")
    print(f"  📊 Tokeny celkem: {total_tokens_all:,} | Cena celkem: ${total_cost_all:.4f}")


if __name__ == "__main__":
    main()