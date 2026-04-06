"""
Abstrakce nad LLM providery.
Podporuje: Gemini, OpenAI, Claude, DeepSeek, Mistral, OllamaCompat.

Model se vždy nastavuje přes experiment.yaml → create_llm().
Temperature se předává z experiment.yaml; None = default provideru.

v2.3: + MistralProvider (Mistral AI SDK)
      generate_text() vrací tuple (text, usage_dict | None).
"""
import time
from abc import ABC, abstractmethod

from token_tracker import (
    extract_usage_gemini,
    extract_usage_openai,
    extract_usage_mistral,
)



class LLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str) -> tuple[str, dict | None]:
        pass


class RetryMixin:
    """Sdílená retry logika pro všechny providery."""

    max_retries: int = 8
    base_delay: float = 30.0
    call_delay: float = 5.0

    def _retry_call(self, func, retryable_codes=(
            "503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED",
            "high demand", "rate_limit", "Too Many Requests", "rate_limit_error",
    )):
        if self.call_delay > 0:
            time.sleep(self.call_delay)

        for attempt in range(1, self.max_retries + 1):
            try:
                return func()
            except Exception as e:
                err = str(e)
                if any(code.lower() in err.lower() for code in retryable_codes) and attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** (attempt - 1)), 240.0)
                    print(f"    ⚠️ Rate Limit / API chyba (pokus {attempt}/{self.max_retries}): {err[:120]}")
                    print(f"    ⏳ Čekám {delay:.0f}s...")
                    time.sleep(delay)
                else:
                    raise


class GeminiProvider(LLMProvider, RetryMixin):
    def __init__(self, api_key: str, model_name: str,
                 temperature: float | None = None,
                 max_retries: int = 8, base_delay: float = 30.0):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model_name
        self.model_name = model_name
        self.temperature = temperature
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> tuple[str, dict | None]:
        from google.genai import types
        temp = self.temperature if self.temperature is not None else 1

        def _call():
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temp),
            )
            text = response.text or ""
            usage = extract_usage_gemini(response)
            return text, usage

        return self._retry_call(_call)


class DeepSeekProvider(LLMProvider, RetryMixin):
    """DeepSeek — OpenAI-kompatibilní API."""
    def __init__(self, api_key: str, model_name: str,
                 temperature: float | None = None,
                 max_retries: int = 8, base_delay: float = 30.0,
                 max_tokens: int = 8192):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = model_name
        self.model_name = model_name
        self.temperature = temperature if temperature is not None else 0.7
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> tuple[str, dict | None]:
        def _call():
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,         # ← PŘIDÁNO
            )
            text = response.choices[0].message.content or ""
            usage = extract_usage_openai(response)
            return text, usage

        return self._retry_call(_call)


class MistralProvider(LLMProvider, RetryMixin):
    """Mistral AI — vlastní SDK (pip install mistralai)."""
    def __init__(self, api_key: str, model_name: str,
                 temperature: float | None = None,
                 max_retries: int = 8, base_delay: float = 30.0,
                 max_tokens: int = 8192):
        from mistralai import Mistral
        self.client = Mistral(api_key=api_key)
        self.model = model_name
        self.model_name = model_name
        self.temperature = temperature if temperature is not None else 0.7
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> tuple[str, dict | None]:
        def _call():
            response = self.client.chat.complete(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            text = response.choices[0].message.content or ""
            usage = extract_usage_mistral(response)
            return text, usage

        return self._retry_call(_call)


# ── Factory ──────────────────────────────────────────────

PROVIDERS = {
    "gemini": GeminiProvider,
    "deepseek": DeepSeekProvider,
    "mistral": MistralProvider,
}


def create_llm(provider: str, api_key: str, model: str,
               temperature: float | None = None,
               **kwargs) -> LLMProvider:
    import inspect

    cls = PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Neznámý provider: {provider}. Dostupné: {list(PROVIDERS.keys())}")

    valid_params = inspect.signature(cls.__init__).parameters
    filtered = {k: v for k, v in kwargs.items() if k in valid_params}

    return cls(api_key=api_key, model_name=model, temperature=temperature, **filtered)