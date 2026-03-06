"""
Abstrakce nad LLM providery.
Umožňuje snadno přepínat mezi modely (Gemini, Claude, OpenAI, ...).
"""
import os
from abc import ABC, abstractmethod
from google import genai


class LLMProvider(ABC):
    """Abstraktní rozhraní pro jakýkoliv LLM model."""

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        pass


class GeminiProvider(LLMProvider):
    """Implementace pro Google Gemini."""

    def __init__(self, api_key: str, model_name: str = 'gemini-3.1-flash-lite-preview'):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        print(f"  LLM Provider: Gemini ({model_name})")

    def generate_text(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return response.text


# Budoucí providery:
# class ClaudeProvider(LLMProvider): ...
# class OpenAIProvider(LLMProvider): ...
# class DeepSeekProvider(LLMProvider): ...