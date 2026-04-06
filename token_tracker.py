"""
Token Tracker — přesné měření tokenů z API response.

Zachytává skutečné tokeny (ne odhad chars//3) z každého LLM volání.
Akumuluje per-run, per-phase, per-model. Počítá cenu.

Integrace:
  1. LLMProvider.generate_text() vrací (text, usage_dict)
  2. TokenTracker.record() akumuluje
  3. Na konci runu: tracker.summary() → do výsledků

Usage dict format (jednotný pro všechny providery):
  {
    "prompt_tokens": int,
    "completion_tokens": int,
    "total_tokens": int,
    "cached_tokens": int | None,   # Gemini/DeepSeek umí cache
  }
"""

from dataclasses import dataclass, field
import time


# ─── Pricing (USD per 1M tokenů, duben 2026) ────────────
# Aktualizuj podle aktuálních ceníků.
# Struktura: model_pattern → {"input": $, "output": $, "cached_input": $ | None}

DEFAULT_PRICING: dict[str, dict[str, float | None]] = {
    # ═══ Gemini (USD per 1M tokenů, duben 2026) ═══
    # Zdroj: ai.google.dev/gemini-api/docs/pricing (2026-04-02)
    # ≤200K context. Pro modely: >200K = 2× cena.
    "gemini-3.1-flash-lite-preview": {
        "input": 0.25,  "output": 1.50,  "cached_input": 0.0625,
    },
    "gemini-2.5-pro": {
        "input": 1.25,  "output": 10.00, "cached_input": 0.3125,
    },
    # ═══ DeepSeek (USD per 1M tokenů) ═══
    # Zdroj: api-docs.deepseek.com/quick_start/pricing
    # deepseek-chat i deepseek-reasoner = V3.2 (128K context)
    # Cache hit = 90% sleva (automatický prefix caching)
    "deepseek-chat": {                          # V3.2 / V4
        "input": 0.28,  "output": 0.42,  "cached_input": 0.028,
    },
    # ═══ Mistral (USD per 1M tokenů) ═══
    # Zdroj: docs.mistral.ai/deployment/ai-studio/pricing
    "mistral-large-latest": {                   # Large 3
        "input": 2.00,  "output": 6.00,  "cached_input": None,
    },
}


@dataclass
class TokenCall:
    """Jeden LLM call."""
    phase: str                      # "planning", "generation", "repair", "fill", ...
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    timestamp: float = field(default_factory=time.time)
    detail: str = ""                # volitelný popis, e.g. "repair_iter3_test_xyz"


class TokenTracker:
    """
    Akumulátor tokenů pro jeden run (1 LLM × 1 API × 1 level × 1 temp × 1 run).

    Použití:
        tracker = TokenTracker(model="gemini-2.0-flash")
        ...
        tracker.record("planning", usage_dict)
        tracker.record("generation", usage_dict)
        tracker.record("repair", usage_dict, detail="iter2_helper")
        ...
        summary = tracker.summary()   # → dict pro JSON výstup
    """

    def __init__(self, model: str, pricing: dict | None = None):
        self.model = model
        self.calls: list[TokenCall] = []
        self._pricing = pricing or DEFAULT_PRICING

    def record(self, phase: str, usage: dict | None, detail: str = ""):
        """Zaznamenej jeden LLM call. usage = None → přeskočí (provider nevrátil data)."""
        if not usage:
            return
        self.calls.append(TokenCall(
            phase=phase,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            cached_tokens=usage.get("cached_tokens", 0) or 0,
            detail=detail,
        ))

    # ─── Agregace ────────────────────────────────────────

    def total_prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.calls)

    def total_completion_tokens(self) -> int:
        return sum(c.completion_tokens for c in self.calls)

    def total_tokens(self) -> int:
        return sum(c.total_tokens for c in self.calls)

    def total_cached_tokens(self) -> int:
        return sum(c.cached_tokens for c in self.calls)

    def call_count(self) -> int:
        return len(self.calls)

    def per_phase(self) -> dict[str, dict]:
        """Agregace per fáze (planning, generation, repair, fill, ...)."""
        phases: dict[str, dict] = {}
        for c in self.calls:
            p = phases.setdefault(c.phase, {
                "calls": 0, "prompt_tokens": 0,
                "completion_tokens": 0, "total_tokens": 0,
                "cached_tokens": 0,
            })
            p["calls"] += 1
            p["prompt_tokens"] += c.prompt_tokens
            p["completion_tokens"] += c.completion_tokens
            p["total_tokens"] += c.total_tokens
            p["cached_tokens"] += c.cached_tokens
        return phases

    # ─── Cost ────────────────────────────────────────────

    def _resolve_pricing(self) -> dict[str, float | None] | None:
        """Najdi pricing pro self.model — přesná shoda nebo substring match."""
        if self.model in self._pricing:
            return self._pricing[self.model]
        for pattern, price in self._pricing.items():
            if pattern in self.model or self.model in pattern:
                return price
        return None

    def cost_usd(self) -> dict:
        """
        Vypočítá cenu v USD.

        Vrací:
          {
            "input_cost": float,
            "output_cost": float,
            "total_cost": float,
            "cached_savings": float,   # kolik ušetřil cache
            "pricing_model": str,      # který pricing se použil
            "pricing_found": bool,
          }
        """
        pricing = self._resolve_pricing()
        if not pricing:
            return {
                "input_cost": 0.0, "output_cost": 0.0,
                "total_cost": 0.0, "cached_savings": 0.0,
                "pricing_model": "unknown",
                "pricing_found": False,
            }

        input_rate = pricing["input"] / 1_000_000       # per token
        output_rate = pricing["output"] / 1_000_000
        cached_rate = (pricing.get("cached_input") or pricing["input"]) / 1_000_000

        total_prompt = self.total_prompt_tokens()
        total_cached = self.total_cached_tokens()
        non_cached_prompt = total_prompt - total_cached
        total_completion = self.total_completion_tokens()

        input_cost = (non_cached_prompt * input_rate) + (total_cached * cached_rate)
        output_cost = total_completion * output_rate
        cached_savings = total_cached * (input_rate - cached_rate)

        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(input_cost + output_cost, 6),
            "cached_savings": round(cached_savings, 6),
            "pricing_model": self.model,
            "pricing_found": True,
        }

    # ─── Summary ─────────────────────────────────────────

    def summary(self) -> dict:
        """Kompletní summary pro JSON výstup."""
        cost = self.cost_usd()
        return {
            "model": self.model,
            "total_calls": self.call_count(),
            "total_prompt_tokens": self.total_prompt_tokens(),
            "total_completion_tokens": self.total_completion_tokens(),
            "total_tokens": self.total_tokens(),
            "total_cached_tokens": self.total_cached_tokens(),
            "per_phase": self.per_phase(),
            "cost_usd": cost,
        }

    def summary_slim(self) -> dict:
        """Slim verze — jen čísla, bez per-phase breakdown."""
        cost = self.cost_usd()
        return {
            "total_calls": self.call_count(),
            "prompt_tokens": self.total_prompt_tokens(),  # Počet input tokenů
            "completion_tokens": self.total_completion_tokens(),  # Počet output tokenů
            "total_tokens": self.total_tokens(),  # Celkový počet
            "cached_tokens": self.total_cached_tokens(),
            "cost_input_usd": cost["input_cost"],  # Cena za input
            "cost_output_usd": cost["output_cost"],  # Cena za output
            "cost_total_usd": cost["total_cost"],  # Cena celkem
            "pricing_found": cost["pricing_found"],
        }


# ─── Extrakce usage z API response per provider ─────────
#
# Tyto funkce se volají v llm_provider.py po každém API callu.
# Vrací jednotný dict nebo None.

def extract_usage_gemini(response) -> dict | None:
    """
    google.genai response.usage_metadata:
      prompt_token_count, candidates_token_count, total_token_count,
      cached_content_token_count (pokud existuje)
    """
    meta = getattr(response, "usage_metadata", None)
    if not meta:
        return None
    return {
        "prompt_tokens": getattr(meta, "prompt_token_count", 0) or 0,
        "completion_tokens": getattr(meta, "candidates_token_count", 0) or 0,
        "total_tokens": getattr(meta, "total_token_count", 0) or 0,
        "cached_tokens": getattr(meta, "cached_content_token_count", 0) or 0,
    }



def extract_usage_mistral(response) -> dict | None:
    """
    Mistral SDK response.usage:
      prompt_tokens, completion_tokens, total_tokens
    """
    usage = getattr(response, "usage", None)
    if not usage:
        return None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        "cached_tokens": 0,
    }


def extract_usage_openai(response) -> dict | None:
    """
    OpenAI-kompatibilní response (DeepSeek, OpenAI, atd.).
    response.usage: prompt_tokens, completion_tokens, total_tokens,
    prompt_cache_hit_tokens (DeepSeek specifické)
    """
    usage = getattr(response, "usage", None)
    if not usage:
        return None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        "cached_tokens": getattr(usage, "prompt_cache_hit_tokens", 0) or 0,
    }