from src.backend.kr8.llm.openai.like import OpenAILike
import os

class OllamaOpenAI(OpenAILike):
    name: str = "Ollama"
    model: str = "tinyllama"
    api_key: str = "ollama"
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")


