# code_assistant.py

from src.backend.kr8.assistant import Assistant
from src.backend.kr8.tools import Toolkit
from src.backend.kr8.tools.code_tools import CodeTools
from typing import Dict, List, Any, Optional, Union
from pydantic import Field
import json
import re

class CodeAssistant(Assistant):
    code_tools: Optional[CodeTools] = Field(default=None, description="CodeTools for code project analysis")

    def __init__(self, llm, tools: List[Any], **kwargs):
        super().__init__(
            name="Code Assistant",
            role="Assist with code project development and analysis",
            llm=llm,
            tools=tools,
            instructions=[
                "Analyze code project files and provide solutions, guidance, and analysis.",
                "Use the knowledge base to access project files and structure.",
                "Provide code snippets, explanations, and best practices for development.",
                "Include summarized dependency information when answering questions about the project.",
                "Support both React and Java projects."
            ],
            **kwargs
        )
        self.code_tools = next((tool for tool in tools if isinstance(tool, CodeTools)), None)

    
    def run(self, query: str, stream: bool = False) -> Union[str, Any]:
        if not self.code_tools:
            return "Error: CodeTools not initialized"
        
        project_name, project_type = self.extract_project_info(query)
        dependency_summary = self.summarize_dependency_graph(project_name, project_type)
        
         #logic to detect visualization or summary requests
        if "visualize project" in query.lower():
            return self.visualize_project(project_name, project_type)
        elif "project summary" in query.lower():
            return self.get_project_summary(project_name, project_type)
        
        context = f"Project type: {project_type}\nDependency summary for project {project_name}:\n{dependency_summary}\n\n"
        full_query = context + query
        return super().run(full_query, stream=stream)

    def extract_project_info(self, query: str) -> tuple:
        project_name = re.search(r'project[:\s]+(\w+)', query, re.IGNORECASE)
        project_name = project_name.group(1) if project_name else "default_project"
        
        if "react" in query.lower():
            project_type = "react"
        elif "java" in query.lower():
            project_type = "java"
        else:
            project_type = "unknown"
        
        return project_name, project_type


    def get_dependency_graph(self, project_name: str, project_type: str) -> Dict:
        doc = self.code_tools.knowledge_base.search(query=f"project:{project_name} type:{project_type}_dependency_graph", num_documents=1)
        if doc:
            return json.loads(doc[0].content)
        return {}

    def find_component(self, project_name: str, component_name: str, project_type: str) -> str:
        result = self.code_tools.find_component(project_name, component_name, project_type)
        return f"Component '{component_name}' in {project_type} project '{project_name}':\n{result}"

    def suggest_code_improvement(self, project_name: str, file_path: str, project_type: str) -> str:
        file_content = self.code_tools.get_file_content(project_name, file_path, project_type)
        if not file_content:
            return f"Error: File {file_path} not found in project {project_name}"
        
        prompt = f"""Analyze the following {project_type} code and suggest improvements for best practices, performance, and readability:

File: {file_path}

{file_content}

Provide specific suggestions and explain the rationale behind each improvement."""

        response = self.llm.run(prompt)
        return f"Code improvement suggestions for {file_path} in {project_type} project '{project_name}':\n{response}"

    def explain_code_snippet(self, project_name: str, file_path: str, start_line: int, end_line: int, project_type: str) -> str:
        code_snippet = self.code_tools.get_code_snippet(project_name, file_path, start_line, end_line, project_type)
        if not code_snippet:
            return f"Error: Could not retrieve code snippet from {file_path} in project {project_name}"
        
        prompt = f"""Explain the following {project_type} code snippet in detail:

File: {file_path}
Lines: {start_line}-{end_line}

{code_snippet}

Provide a comprehensive explanation including:
1. The purpose of this code
2. How it works
3. Any important patterns or concepts used
4. Potential implications or side effects"""

        response = self.llm.run(prompt)
        return f"Explanation of code snippet from {file_path} in {project_type} project '{project_name}':\n{response}"

    def solve_code_problem(self, problem_description: str, project_name: str, project_type: str) -> str:
        relevant_files = self.code_tools.knowledge_base.search(query=f"project:{project_name} type:{project_type}_file {problem_description}", num_documents=5)
        
        context = f"Problem in {project_type} project '{project_name}': {problem_description}\n\nRelevant files:\n"
        for file in relevant_files:
            context += f"- {file.name}\n"
            context += f"{file.content[:500]}...\n\n"  # Include a preview of each file
        
        prompt = f"""{context}

Based on the problem description and the relevant files, provide a detailed solution to the problem. Include:
1. A clear explanation of the issue
2. Step-by-step instructions to resolve the problem
3. Any code snippets or modifications needed
4. Explanation of why this solution works"""

        response = self.llm.run(prompt)
        return f"Solution for problem in {project_type} project '{project_name}':\n{response}"

    def design_feature_solution(self, feature_description: str, project_name: str, project_type: str) -> str:
        project_structure = self.analyze_project_structure(project_name, project_type)
        
        prompt = f"""Design a solution for the following feature in {project_type} project '{project_name}':

Feature description: {feature_description}

Current project structure:
{project_structure}

Provide a comprehensive design solution including:
1. High-level architecture or component design
2. Key classes or functions that need to be implemented
3. Any changes required to existing project structure
4. Potential challenges and how to address them
5. Best practices and patterns to follow for this feature
6. Any performance or scalability considerations"""

        response = self.llm.run(prompt)
        return f"Feature design solution for {project_type} project '{project_name}':\n{response}"

    def analyze_test_coverage(self, project_name: str, project_type: str) -> str:
        test_files = self.code_tools.knowledge_base.search(query=f"project:{project_name} type:{project_type}_file test", num_documents=50)
        total_files = self.code_tools.knowledge_base.search(query=f"project:{project_name} type:{project_type}_file", num_documents=1000)
        
        test_file_count = len(test_files)
        total_file_count = len(total_files)
        coverage_percentage = (test_file_count / total_file_count) * 100 if total_file_count > 0 else 0
        
        prompt = f"""Analyze the test coverage for {project_type} project '{project_name}':

Total files: {total_file_count}
Test files: {test_file_count}
Estimated coverage: {coverage_percentage:.2f}%

Provide a detailed analysis including:
1. Assessment of the current test coverage
2. Identification of areas that may need more testing
3. Suggestions for improving test coverage
4. Best practices for testing in {project_type} projects
5. Any tools or frameworks recommended for better testing"""

        response = self.llm.run(prompt)
        return f"Test coverage analysis for {project_type} project '{project_name}':\n{response}"

    def analyze_security(self, project_name: str, project_type: str) -> str:
        all_files = self.code_tools.knowledge_base.search(query=f"project:{project_name} type:{project_type}_file", num_documents=1000)
        
        security_concerns = {
            "react": [
                "XSS vulnerabilities",
                "Insecure dependencies",
                "Exposure of sensitive information",
                "CSRF protection",
                "Improper access control"
            ],
            "java": [
                "SQL injection",
                "Improper error handling",
                "Insecure cryptographic storage",
                "Insufficient logging and monitoring",
                "Broken authentication and session management"
            ]
        }
        
        prompt = f"""Perform a security analysis for {project_type} project '{project_name}':

Total files analyzed: {len(all_files)}

Key security concerns for {project_type} projects:
{json.dumps(security_concerns[project_type], indent=2)}

Analyze the project for these and other potential security issues. Provide a detailed report including:
1. Identification of potential security vulnerabilities
2. Assessment of the overall security posture
3. Recommendations for addressing any identified issues
4. Best practices for improving security in {project_type} projects
5. Suggestions for security tools or libraries that could be beneficial"""

        response = self.llm.run(prompt)
        return f"Security analysis for {project_type} project '{project_name}':\n{response}"

    def analyze_performance(self, project_name: str, project_type: str) -> str:
        all_files = self.code_tools.knowledge_base.search(query=f"project:{project_name} type:{project_type}_file", num_documents=1000)
        
        performance_concerns = {
            "react": [
                "Unnecessary re-renders",
                "Large bundle sizes",
                "Unoptimized images",
                "Inefficient state management",
                "Excessive API calls"
            ],
            "java": [
                "Inefficient algorithms",
                "Memory leaks",
                "Unoptimized database queries",
                "Thread synchronization issues",
                "Excessive object creation"
            ]
        }
        
        prompt = f"""Perform a performance analysis for {project_type} project '{project_name}':

Total files analyzed: {len(all_files)}

Key performance concerns for {project_type} projects:
{json.dumps(performance_concerns[project_type], indent=2)}

Analyze the project for these and other potential performance issues. Provide a detailed report including:
1. Identification of potential performance bottlenecks
2. Assessment of the overall performance characteristics
3. Recommendations for optimizing performance
4. Best practices for improving performance in {project_type} projects
5. Suggestions for performance profiling tools or techniques"""

        response = self.llm.run(prompt)
        return f"Performance analysis for {project_type} project '{project_name}':\n{response}"

    def get_project_structure(self, project_name: str, project_type: str) -> str:
        structure = self.code_tools.analyze_project_structure(project_name, project_type)
        return f"Project structure for {project_type} project '{project_name}':\n{json.dumps(structure, indent=2)}"