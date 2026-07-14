import logging
from google import genai
from google.genai import types
from django.conf import settings
from .providers import LLMProvider, EmbeddingProvider, RateLimitError, ServiceUnavailableError

logger = logging.getLogger(__name__)

import os
from dotenv import load_dotenv

class GeminiProvider(LLMProvider, EmbeddingProvider):
    def __init__(self):
        # Dynamically reload env file to pick up additions without restarting server
        load_dotenv(settings.BASE_DIR / '.env', override=True)
        api_key = os.getenv('GEMINI_API_KEY', '') or getattr(settings, 'GEMINI_API_KEY', '')
        # Strip surrounding quotes if the user wrapped the key in quotes in .env
        api_key = api_key.strip("'\"")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in Django settings or .env file.")
        self.client = genai.Client(api_key=api_key)
        self.llm_model = 'gemini-flash-latest'
        self.embedding_model = 'gemini-embedding-001'

    def generate(self, prompt: str, system_instruction: str = None) -> str:
        try:
            config = None
            if system_instruction:
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
            
            response = self.client.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config=config
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            err_msg = str(e).lower()
            if "429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg:
                raise RateLimitError("Gemini API rate limit or quota exceeded. Please wait a few seconds and try again.") from e
            if "503" in err_msg or "unavailable" in err_msg:
                raise ServiceUnavailableError("Gemini API is temporarily experiencing high demand. Please try again in a few seconds.") from e
            raise

    def embed_text(self, text: str) -> list[float]:
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text
            )
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
            raise ValueError("Failed to retrieve embeddings from Gemini API response.")
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            err_msg = str(e).lower()
            if "429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg:
                raise RateLimitError("Gemini API rate limit or quota exceeded. Please wait a few seconds and try again.") from e
            if "503" in err_msg or "unavailable" in err_msg:
                raise ServiceUnavailableError("Gemini API is temporarily experiencing high demand. Please try again in a few seconds.") from e
            raise

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=texts
            )
            if response.embeddings:
                return [emb.values for emb in response.embeddings]
            raise ValueError("Failed to retrieve embeddings from Gemini API response.")
        except Exception as e:
            logger.error(f"Gemini multi-embedding error: {e}")
            err_msg = str(e).lower()
            if "429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg:
                raise RateLimitError("Gemini API rate limit or quota exceeded. Please wait a few seconds and try again.") from e
            if "503" in err_msg or "unavailable" in err_msg:
                raise ServiceUnavailableError("Gemini API is temporarily experiencing high demand. Please try again in a few seconds.") from e
            raise


