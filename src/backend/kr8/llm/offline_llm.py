# src/kr8/llm/offline_llm.py

from typing import List, Iterator, Mapping, Any
from src.backend.kr8.llm.base import LLM
from src.backend.kr8.llm.message import Message
from src.backend.kr8.utils.log import logger

class OfflineLLM(LLM):
    name: str = "Offline LLM"
    model: str = "offline-model" 

    def invoke(self, messages: List[Message]) -> Mapping[str, Any]:
        logger.info("Using offline LLM mode")
        return {
            "message": {
                "role": "assistant",
                "content": "I'm currently in offline mode. I can engage in general conversation, but I can't access real-time data or perform complex tasks. How can I assist you within these limitations? Simples!"
            }
        }

    def invoke_stream(self, messages: List[Message]) -> Iterator[Mapping[str, Any]]:
        logger.info("Using offline LLM mode (stream)")
        yield {
            "message": {
                "role": "assistant",
                "content": "I'm currently in offline mode. I can engage in general conversation, but I can't access real-time data or perform complex tasks. How can I assist you within these limitations? Simples!"
            }
        }

    def response(self, messages: List[Message]) -> str:
        return self.invoke(messages)["message"]["content"]

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        yield self.invoke(messages)["message"]["content"]