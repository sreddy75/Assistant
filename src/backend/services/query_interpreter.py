# query_interpreter.py

import json
from src.backend.services.azure_devops_schema_manager import AzureDevOpsSchemaManager
from src.backend.kr8.llm.base import LLM
from src.backend.kr8.llm.message import Message

class QueryInterpreter:
    def __init__(self, schema_manager: AzureDevOpsSchemaManager):        
        self.schema_manager = schema_manager

    def interpret_query(self, query: str):
        schema = self.schema_manager.get_schema()
        prompt = f"""
        Given the following Azure DevOps API schema and user query, determine:
        1. The most relevant API endpoint(s) to call
        2. Any parameters needed for the API call(s)
        3. Any post-processing steps needed on the API response

        Schema:
        {json.dumps(schema, indent=2)}

        Query:
        {query}

        Response (in JSON format):
        {{
            "endpoints": [
                {{
                    "path": "<api_path>",
                    "method": "<HTTP_METHOD>",
                    "parameters": {{
                        "<param_name>": "<param_value>"
                    }}
                }}
            ],
            "post_processing": [
                "Step 1: ...",
                "Step 2: ...",
                ...
            ]
        }}
        """
        messages = [Message(role="user", content=prompt)]
        response = self.llm.response(messages)
        return json.loads(response)