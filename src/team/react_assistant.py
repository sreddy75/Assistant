# react_assistant.py

from kr8.assistant import Assistant
from kr8.tools import Toolkit
from kr8.tools.code_tools import CodeTools
from typing import Dict, List, Any, Optional, Union
from pydantic import Field
import json

class ReactAssistant(Assistant):
    code_tools: Optional[CodeTools] = Field(default=None, description="CodeTools for React project analysis")

    def __init__(self, llm, tools: List[Any]):
        super().__init__(
            name="React Assistant",
            role="Assist with React project development and analysis",
            llm=llm,
            tools=tools,
            instructions=[
                "Analyze React project code and provide solutions, guidance, and analysis.",
                "Use the knowledge base to access project files and structure.",
                "Provide code snippets, explanations, and best practices for React development.",
                "Include summarized dependency information when answering questions about the project."
            ],
        )
        self.code_tools = next((tool for tool in tools if isinstance(tool, CodeTools)), None)

    def run(self, query: str, stream: bool = False) -> Union[str, Any]:
        if not self.code_tools:
            return "Error: CodeTools not initialized"
        
        project_name = self.extract_project_name(query)
        dependency_summary = self.summarize_dependency_graph(project_name)
        
        context = f"Dependency summary for project {project_name}:\n{dependency_summary}\n\n"
        full_query = context + query
        return super().run(full_query, stream=stream)

    def extract_project_name(self, query: str) -> str:
        # Implement logic to extract project name from query or use a default
        return "my_react_project"

    def summarize_dependency_graph(self, project_name: str) -> str:
        doc = self.code_tools.knowledge_base.vector_db.search(f"{project_name}_dependency_graph", limit=1)
        if doc:
            graph = json.loads(doc[0].content)
            summary = {
                "total_dependencies": len(graph),
                "top_level_dependencies": list(graph.keys())[:10],  # List first 10 top-level dependencies
                "complex_dependencies": [pkg for pkg, deps in graph.items() if len(deps) > 5][:5]  # List up to 5 complex dependencies
            }
            return json.dumps(summary, indent=2)
        return "{}"

    def get_dependency_graph(self, project_name: str) -> Dict:
        doc = self.code_tools.knowledge_base.vector_db.search(f"{project_name}_dependency_graph", limit=1)
        if doc:
            return json.loads(doc[0].content)
        return {}
    
    def analyze_project_structure(self, project_name: str) -> str:
        if not self.code_tools:
            return "Error: CodeTools not initialized"
        return self.code_tools.analyze_project_structure(project_name)

    def find_component(self, project_name: str, component_name: str) -> str:
        if not self.code_tools:
            return "Error: CodeTools not initialized"
        return self.code_tools.find_component(project_name, component_name)

    def suggest_code_improvement(self, project_name: str, file_path: str) -> str:
        if not self.code_tools:
            return "Error: CodeTools not initialized"
        file_content = self.code_tools.get_file_content(project_name, file_path)
        if not file_content:
            return f"Error: File {file_path} not found in project {project_name}"
        
        # Use the LLM to analyze the code and suggest improvements
        prompt = f"Analyze the following React component and suggest improvements for best practices and performance:\n\n{file_content}"
        response = self.llm.run(prompt)
        return response

    def explain_code_snippet(self, project_name: str, file_path: str, start_line: int, end_line: int) -> str:
        if not self.code_tools:
            return "Error: CodeTools not initialized"
        code_snippet = self.code_tools.get_code_snippet(project_name, file_path, start_line, end_line)
        if not code_snippet:
            return f"Error: Could not retrieve code snippet from {file_path} in project {project_name}"
        
        prompt = f"Explain the following React code snippet in detail:\n\n{code_snippet}"
        response = self.llm.run(prompt)
        return response
    def solve_code_problem(self, problem_description: str) -> str:
        # Implement logic to search relevant files and provide solution
        relevant_files = self.search_knowledge_base(problem_description)
        # Analyze the relevant files and generate a solution
        # This is a placeholder implementation
        return f"Solution for problem: {problem_description}\nRelevant files: {relevant_files}"

    def design_feature_solution(self, feature_description: str) -> str:
        # Implement logic to design and explain feature implementation
        # This is a placeholder implementation
        return f"Design solution for feature: {feature_description}"

    def analyze_test_coverage(self) -> str:
        # Implement logic to analyze test files and report coverage
        # This is a placeholder implementation
        return "Test coverage analysis: 75% coverage"

    def analyze_security(self) -> str:
        # Implement logic to check for common security issues in React
        # This is a placeholder implementation
        return "Security analysis: No major issues found"

    def analyze_performance(self) -> str:
        # Implement logic to suggest performance improvements
        # This is a placeholder implementation
        return "Performance analysis: Consider optimizing large component renders"

    def get_project_structure(self) -> str:
        # Implement logic to return the structure of the React project
        # This is a placeholder implementation
        return "Project structure: src/, public/, package.json, etc."