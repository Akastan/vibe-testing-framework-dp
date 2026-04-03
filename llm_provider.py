"""
Abstrakce nad LLM providery.
Podporuje: Gemini, OpenAI, Claude, DeepSeek, OllamaCompat (lokální modely).

Model se vždy nastavuje přes experiment.yaml → create_llm().
Temperature se předává z experiment.yaml; None = default provideru.

v2.2: generate_text() vrací tuple (text, usage_dict | None).
      TrackingLLMWrapper v main.py to rozbalí transparentně.
      usage_dict formát: {"prompt_tokens": int, "completion_tokens": int,
                          "total_tokens": int, "cached_tokens": int}
"""
import re
import time
from abc import ABC, abstractmethod

from token_tracker import (
    extract_usage_gemini,
    extract_usage_openai,
    extract_usage_claude,
)


class LLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str) -> tuple[str, dict | None]:
        pass


class RetryMixin:
    """Sdílená retry logika pro všechny providery."""
    max_retries: int = 5
    base_delay: float = 10.0
    time.sleep(15)  # Pro free Gemini API - max 15 RPM

    def _retry_call(self, func, retryable_codes=(
        "503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED",
        "high demand", "rate_limit",
    )):
        for attempt in range(1, self.max_retries + 1):
            try:
                return func()
            except Exception as e:
                err = str(e)
                if any(code in err for code in retryable_codes) and attempt < self.max_retries:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    print(f"    ⚠️ API chyba (pokus {attempt}/{self.max_retries}): {err[:120]}")
                    print(f"    ⏳ Čekám {delay:.0f}s...")
                    time.sleep(delay)
                else:
                    raise


class GeminiProvider(LLMProvider, RetryMixin):
    def __init__(self, api_key: str, model_name: str,
                 temperature: float | None = None,
                 max_retries: int = 5, base_delay: float = 10.0):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model_name       # pro TokenTracker pricing lookup
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


class OpenAIProvider(LLMProvider, RetryMixin):
    def __init__(self, api_key: str, model_name: str,
                 temperature: float | None = None,
                 max_retries: int = 5, base_delay: float = 10.0):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model_name
        self.model_name = model_name
        self.temperature = temperature if temperature is not None else 0.7
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> tuple[str, dict | None]:
        def _call():
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            text = response.choices[0].message.content or ""
            usage = extract_usage_openai(response)
            return text, usage

        return self._retry_call(_call)


class ClaudeProvider(LLMProvider, RetryMixin):
    def __init__(self, api_key: str, model_name: str,
                 temperature: float | None = None,
                 max_retries: int = 5, base_delay: float = 10.0):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model_name
        self.model_name = model_name
        self.temperature = temperature
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> tuple[str, dict | None]:
        def _call():
            kwargs = dict(
                model=self.model_name,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            if self.temperature is not None:
                kwargs["temperature"] = self.temperature
            response = self.client.messages.create(**kwargs)
            text = response.content[0].text
            usage = extract_usage_claude(response)
            return text, usage

        return self._retry_call(_call)


class DeepSeekProvider(LLMProvider, RetryMixin):
    """DeepSeek používá OpenAI-kompatibilní API."""
    def __init__(self, api_key: str, model_name: str,
                 temperature: float | None = None,
                 max_retries: int = 5, base_delay: float = 10.0):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = model_name
        self.model_name = model_name
        self.temperature = temperature if temperature is not None else 0.7
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> tuple[str, dict | None]:
        def _call():
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            text = response.choices[0].message.content or ""
            usage = extract_usage_openai(response)  # OpenAI-kompatibilní formát
            return text, usage

        return self._retry_call(_call)


class OllamaCompatProvider(LLMProvider, RetryMixin):
    def __init__(self, api_key: str, model_name: str,
                 temperature: float | None = None,
                 max_retries: int = 5, base_delay: float = 10.0,
                 base_url: str = "",
                 max_tokens: int = 8192,
                 num_ctx: int = 32768,
                 verify_ssl: bool = False):
        import httpx
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(verify=verify_ssl),
        )
        self.model = model_name
        self.model_name = model_name
        self.temperature = temperature if temperature is not None else 0.4
        self.max_tokens = max_tokens
        self.num_ctx = num_ctx
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> tuple[str, dict | None]:
        def _call():
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                extra_body={"options": {"num_ctx": self.num_ctx}},
            )
            raw = response.choices[0].message.content or ""
            text = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            usage = extract_usage_openai(response)  # OpenAI-kompatibilní SDK
            return text, usage

        return self._retry_call(_call)


# ── Factory ──────────────────────────────────────────────

PROVIDERS = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "deepseek": DeepSeekProvider,
    "ollama_compat": OllamaCompatProvider,
}


def create_llm(provider: str, api_key: str, model: str,
               temperature: float | None = None,
               **kwargs) -> LLMProvider:
    """
    Vytvoří LLM provider podle názvu. Model a temperature se berou z experiment.yaml.
    Extra kwargs (base_url, max_tokens, num_ctx, verify_ssl) se předají jen providerům,
    které je podporují.
    """
    import inspect

    cls = PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Neznámý provider: {provider}. Dostupné: {list(PROVIDERS.keys())}")

    # Předej jen kwargs které konstruktor přijímá
    valid_params = inspect.signature(cls.__init__).parameters
    filtered = {k: v for k, v in kwargs.items() if k in valid_params}

    return cls(api_key=api_key, model_name=model, temperature=temperature, **filtered)