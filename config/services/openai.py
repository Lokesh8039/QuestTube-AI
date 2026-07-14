import logging
from openai import OpenAI
from django.conf import settings
from .providers import LLMProvider, EmbeddingProvider

logger = logging.getLogger(__name__)

import os
from dotenv import load_dotenv

class OpenAIProvider(LLMProvider, EmbeddingProvider):
    def __init__(self):
        # Dynamically reload env file to pick up additions without restarting server
        load_dotenv(settings.BASE_DIR / '.env', override=True)
        api_key = os.getenv('OPENAI_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')
        # Strip surrounding quotes if the user wrapped the key in quotes in .env
        api_key = api_key.strip("'\"")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in Django settings or .env file.")
        self.client = OpenAI(api_key=api_key)
        self.llm_model = 'gpt-4o-mini'
        self.embedding_model = 'text-embedding-3-small'

    def generate(self, prompt: str, system_instruction: str = None) -> str:
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise

    def embed_text(self, text: str) -> list[float]:
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
                dimensions=768  # Configure to return 768 dimensions to match Gemini dimension
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts,
                dimensions=768
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"OpenAI multi-embedding error: {e}")
            raise
