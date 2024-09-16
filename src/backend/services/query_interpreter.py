import re
from src.backend.kr8.llm.base import LLM
from src.backend.kr8.llm.message import Message

class QueryInterpreter:
    def __init__(self, llm: LLM):
        self.llm = llm

    def categorize_query(self, query: str):
        prompt = f"Categorize the following project management query:\n\n{query}\n\nCategory:"
        messages = [Message(role="user", content=prompt)]
        response = self.llm.response(messages)
        return response.strip()

    def extract_entities(self, query: str):
        prompt = f"Extract project and team names from the following query:\n\n{query}\n\nEntities:"
        entities = self.llm.generate(prompt)
        return self._parse_entities(entities)

    def _parse_entities(self, entities: str):
        project = re.search(r"Project: (.+)", entities)
        team = re.search(r"Team: (.+)", entities)
        return {
            "project": project.group(1) if project else None,
            "team": team.group(1) if team else None
        }