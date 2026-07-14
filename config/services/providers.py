from abc import ABC, abstractmethod

class RateLimitError(Exception):
    """Exception raised when an AI API rate limit is exceeded."""
    pass

class ServiceUnavailableError(Exception):
    """Exception raised when the AI API is temporarily unavailable due to high demand."""
    pass

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_instruction: str = None) -> str:
        """
        Generate text response from LLM based on prompt.
        """
        pass

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """
        Generate a single vector embedding for text.
        """
        pass

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate a list of vector embeddings for multiple texts.
        """
        pass

