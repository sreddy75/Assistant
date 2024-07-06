from kr8.llm.openai.like import OpenAILike


class OllamaOpenAI(OpenAILike):
    name: str = "Ollama"
    model: str = "llama3"
    api_key: str = "ollama"
    base_url: str = "http://localhost:11434/v1"
