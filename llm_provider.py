"""
Abstrakce nad LLM providery.
Podporuje: Gemini, OpenAI, Claude, DeepSeek.

Model se vždy nastavuje přes experiment.yaml → create_llm().
"""
import time
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        pass


class RetryMixin:
    """Sdílená retry logika pro všechny providery."""
    max_retries: int = 5
    base_delay: float = 10.0

    def _retry_call(self, func, retryable_codes=("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "high demand", "rate_limit")):
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
                 max_retries: int = 5, base_delay: float = 10.0):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> str:
        def _call():
            return self.client.models.generate_content(
                model=self.model_name, contents=prompt
            ).text
        return self._retry_call(_call)


class OpenAIProvider(LLMProvider, RetryMixin):
    def __init__(self, api_key: str, model_name: str,
                 max_retries: int = 5, base_delay: float = 10.0):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> str:
        def _call():
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content
        return self._retry_call(_call)


class ClaudeProvider(LLMProvider, RetryMixin):
    def __init__(self, api_key: str, model_name: str,
                 max_retries: int = 5, base_delay: float = 10.0):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model_name = model_name
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> str:
        def _call():
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        return self._retry_call(_call)


class DeepSeekProvider(LLMProvider, RetryMixin):
    """DeepSeek používá OpenAI-kompatibilní API."""
    def __init__(self, api_key: str, model_name: str,
                 max_retries: int = 5, base_delay: float = 10.0):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model_name = model_name
        self.max_retries = max_retries
        self.base_delay = base_delay

    def generate_text(self, prompt: str) -> str:
        def _call():
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content
        return self._retry_call(_call)


# ── Factory ──────────────────────────────────────────────

PROVIDERS = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "deepseek": DeepSeekProvider,
}

def create_llm(provider: str, api_key: str, model: str) -> LLMProvider:
    """Vytvoří LLM provider podle názvu. Model se bere z experiment.yaml."""
    cls = PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Neznámý provider: {provider}. Dostupné: {list(PROVIDERS.keys())}")
    return cls(api_key=api_key, model_name=model)