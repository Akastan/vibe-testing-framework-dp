import os
from abc import ABC, abstractmethod
from google import genai
from google.genai import types

class LLMProvider(ABC):
    """Abstraktní třída definující rozhraní pro jakýkoliv LLM model."""

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        pass


class GeminiProvider(LLMProvider):
    """Implementace pro Google Gemini (nyní verze 2.5 Flash)."""

    #def __init__(self, api_key: str, model_name: str = 'gemini-2.5-flash'):
    def __init__(self, api_key: str, model_name: str = 'gemini-3.1-flash-lite-preview'):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate_text(self, prompt: str) -> str:
        # Konfigurace pro delší výstupy a konzistentní formát
        """
        config = genai.types.GenerationConfig(
            max_output_tokens=8192,  # Zabrání useknutí dlouhého kódu v půlce!
            temperature=0.2  # Nižší teplota = spolehlivější kód
        )
        """

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            #config=config
        )
        return response.text

# Zde v budoucnu:
# class ClaudeProvider(LLMProvider): ...
# class OpenAIProvider(LLMProvider): ...