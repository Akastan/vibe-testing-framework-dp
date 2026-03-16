"""
Abstrakce nad LLM providery.
Umožňuje snadno přepínat mezi modely (Gemini, Claude, OpenAI, ...).
"""
import time
from abc import ABC, abstractmethod
from google import genai


class LLMProvider(ABC):
    """Abstraktní rozhraní pro jakýkoliv LLM model."""

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        pass


class GeminiProvider(LLMProvider):
    """Implementace pro Google Gemini s automatickým retry."""

    def __init__(self, api_key: str, model_name: str = 'gemini-3.1-flash-lite-preview',
                 max_retries: int = 5, base_delay: float = 10.0):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.max_retries = max_retries
        self.base_delay = base_delay
        print(f"  LLM Provider: Gemini ({model_name})")

    def generate_text(self, prompt: str) -> str:
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                return response.text

            except Exception as e:
                error_str = str(e)
                is_retryable = any(code in error_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "high demand"])

                if is_retryable and attempt < self.max_retries:
                    # Exponential backoff: 10s, 20s, 40s, 80s, ...
                    delay = self.base_delay * (2 ** (attempt - 1))
                    print(f"    ⚠️ API chyba (pokus {attempt}/{self.max_retries}): {error_str[:100]}")
                    print(f"    ⏳ Čekám {delay:.0f}s před dalším pokusem...")
                    time.sleep(delay)
                else:
                    raise  # Neretryovatelná chyba nebo vyčerpány pokusy


# Budoucí providery:
# class ClaudeProvider(LLMProvider): ...
# class OpenAIProvider(LLMProvider): ...