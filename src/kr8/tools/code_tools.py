# code_tools.py

from typing import Dict, Optional
from kr8.tools import Toolkit
from kr8.document import Document
from kr8.utils.log import logger
import os

class CodeTools(Toolkit):
    def __init__(self, knowledge_base=None):
        super().__init__(name="code_tools")
        self.knowledge_base = knowledge_base
        self.register(self.load_react_project)

    def load_react_project(self, project_name: str, directory_content: Dict[str, str]) -> str:
        project_namespace = f"react_project_{project_name}"
        supported_extensions = ['.js', '.jsx', '.ts', '.tsx', '.css', '.scss', '.json', '.html', '.md', '.yml', '.yaml', '.env']
        
        for file_path, file_content in directory_content.items():
            _, ext = os.path.splitext(file_path)
            if ext in supported_extensions or os.path.basename(file_path) in ['package.json', '.gitignore', '.eslintrc', '.prettierrc', 'tsconfig.json']:
                doc = Document(
                    name=file_path,
                    content=file_content,
                    meta_data={
                        "project": project_name,
                        "type": "react_file",
                        "file_type": ext
                    }
                )
                # Remove the 'collection' argument
                self.knowledge_base.load_document(doc)
        
        logger.info(f"React project '{project_name}' loaded successfully")
        return f"React project '{project_name}' loaded successfully"
            
    def analyze_project_structure(self, project_name: str) -> str:
        project_namespace = f"react_project_{project_name}"
        files = self.knowledge_base.search(query=f"project:{project_name}", num_documents=1000)
        
        structure = {}
        for file in files:
            path = file.name.split('/')
            current = structure
            for part in path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[path[-1]] = "file"
        
        return json.dumps(structure, indent=2)

    def find_component(self, project_name: str, component_name: str) -> str:
        project_namespace = f"react_project_{project_name}"
        files = self.knowledge_base.search(query=f"project:{project_name} {component_name}", num_documents=5)
        
        results = []
        for file in files:
            if component_name.lower() in file.name.lower():
                results.append(f"Found in {file.name}:\n{file.content[:200]}...")
        
        return "\n\n".join(results) if results else f"Component {component_name} not found"

    def get_file_content(self, project_name: str, file_path: str) -> Optional[str]:
        project_namespace = f"react_project_{project_name}"
        files = self.knowledge_base.search(query=f"project:{project_name} name:{file_path}", num_documents=1)
        return files[0].content if files else None

    def get_code_snippet(self, project_name: str, file_path: str, start_line: int, end_line: int) -> Optional[str]:
        content = self.get_file_content(project_name, file_path)
        if content:
            lines = content.split('\n')
            return '\n'.join(lines[start_line-1:end_line])
        return None