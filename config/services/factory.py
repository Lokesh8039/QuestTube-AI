from django.conf import settings
from .gemini import GeminiProvider
from .openai import OpenAIProvider

def get_llm_provider():
    provider_name = getattr(settings, 'LLM_PROVIDER', 'gemini').lower()
    if provider_name == 'gemini':
        return GeminiProvider()
    elif provider_name == 'openai':
        return OpenAIProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")

def get_embedding_provider():
    provider_name = getattr(settings, 'LLM_PROVIDER', 'gemini').lower()
    if provider_name == 'gemini':
        return GeminiProvider()
    elif provider_name == 'openai':
        return OpenAIProvider()
    else:
        raise ValueError(f"Unknown Embedding provider: {provider_name}")
