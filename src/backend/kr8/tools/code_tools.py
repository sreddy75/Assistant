# code_tools.py

import json
import os
from sqlite3 import IntegrityError
from typing import Callable, Dict, Optional
from src.backend.kr8.tools import Toolkit
from src.backend.kr8.document import Document
from src.backend.kr8.utils.log import logger
from src.backend.utils.npm_utils import generate_dependency_graph as generate_react_dependency_graph
from src.backend.utils.java_utils import generate_java_dependency_graph, analyze_java_project
from typing import Dict, Callable, List
import networkx as nx
import matplotlib.pyplot as plt
import graphviz
from src.backend.kr8.knowledge.base import AssistantKnowledge

class CodeTools(Toolkit):
    def __init__(self, knowledge_base: AssistantKnowledge):
        super().__init__(name="code_tools")
        self.knowledge_base = knowledge_base

        # Register methods as functions
        self.register(self.load_project)
        self.register(self.find_component)
        self.register(self.get_file_content)
        self.register(self.get_code_snippet)
        self.register(self.get_dependency_graph)
        
    def _get_namespace(self, project_name, project_type):
        return f"{project_type}_{project_name}"

    def _upsert_document(self, doc, namespace):
        try:
            self.knowledge_base.vector_db.upsert([doc], namespace=namespace)
            logger.info(f"Upserted file {doc.name} to vector database in namespace {namespace}")
        except AttributeError:
            try:
                self.knowledge_base.vector_db.insert([doc], namespace=namespace)
                logger.info(f"Inserted file {doc.name} to vector database in namespace {namespace}")
            except IntegrityError:
                logger.warning(f"Document {doc.name} already exists in the database. Skipping insertion.")
    
    def load_project(self, project_name: str, project_type: str, directory_content: Dict[str, str], progress_callback: Callable[[float, str], None] = None) -> str:
        namespace = self._get_namespace(project_name, project_type)
        if project_type == "react":
            return self._load_react_project(project_name, directory_content, progress_callback)
        elif project_type == "java":
            return self._load_java_project(project_name, directory_content, progress_callback)
        else:
            return f"Unsupported project type: {project_type}"

    def _load_react_project(self, project_name: str, directory_content: Dict[str, str], progress_callback: Callable[[float, str], None] = None) -> str:
        project_namespace = f"react_project_{project_name}"
        supported_extensions = ['.js', '.jsx', '.ts', '.tsx', '.css', '.scss', '.json', '.html', '.md', '.yml', '.yaml', '.env']
        
        total_files = len(directory_content)
        processed_files = 0
        package_json = None

        for file_path, file_content in directory_content.items():
            _, ext = os.path.splitext(file_path)
            
            if file_path.endswith('package.json'):
                package_json = json.loads(file_content)
                continue

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
                self._upsert_document(doc)

            processed_files += 1
            if progress_callback:
                progress = processed_files / total_files
                progress_callback(progress, f"Processing file {processed_files} of {total_files}: {file_path}")

        if package_json:
            dependency_graph = generate_react_dependency_graph(package_json)
            self._store_dependency_graph(project_name, dependency_graph, "react")

        if progress_callback:
            progress_callback(1.0, f"Processed all files for {project_name}")

        return f"React project '{project_name}' loaded successfully. Processed {processed_files} files and generated dependency graph."

    def _load_java_project(self, project_name: str, directory_content: Dict[str, str], progress_callback: Callable[[float, str], None] = None) -> str:
        print(f"Starting to load Java project: {project_name}")
        project_namespace = f"java_project_{project_name}"
        supported_extensions = ['.java', '.xml', '.properties', '.gradle', '.md', '.yml', '.yaml']
        
        total_files = len(directory_content)
        processed_files = 0
        pom_xml = None
        build_gradle = None

        print(f"Total files to process: {total_files}")

        all_files = self._get_all_files(directory_content)
        total_files = len(all_files)

        for file_path, file_content in all_files.items():
            try:
                _, ext = os.path.splitext(file_path)
                
                print(f"Processing file: {file_path}")

                if file_path.endswith('pom.xml'):
                    pom_xml = file_content
                    print("Found pom.xml")
                elif file_path.endswith('build.gradle'):
                    build_gradle = file_content
                    print("Found build.gradle")

                if ext in supported_extensions or os.path.basename(file_path) in ['pom.xml', 'build.gradle', '.gitignore']:
                    doc = Document(
                        name=file_path,
                        content=file_content,
                        meta_data={
                            "project": project_name,
                            "type": "java_file",
                            "file_type": ext
                        }
                    )
                    self._upsert_document(doc)
                    print(f"Upserted document: {file_path}")

                processed_files += 1
                if progress_callback:
                    progress = processed_files / total_files
                    progress_callback(progress, f"Processing file {processed_files} of {total_files}: {file_path}")

            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")
                import traceback
                print(traceback.format_exc())

        print("Finished processing all files")

        try:
            if pom_xml or build_gradle:
                print("Generating dependency graph")
                dependency_graph = generate_java_dependency_graph(pom_xml, build_gradle)
                self._store_dependency_graph(project_name, dependency_graph, "java")
                print("Dependency graph generated and stored")
        except Exception as e:
            print(f"Error generating dependency graph: {str(e)}")
            import traceback
            print(traceback.format_exc())

        try:
            print("Analyzing Java project structure")
            project_analysis = self._analyze_java_project_structure(all_files)
            self._store_project_analysis(project_name, project_analysis, "java")
            print("Project analysis completed and stored")
        except Exception as e:
            print(f"Error analyzing project structure: {str(e)}")
            import traceback
            print(traceback.format_exc())

        if progress_callback:
            progress_callback(1.0, f"Processed all files for {project_name}")

        return f"Java project '{project_name}' loaded successfully. Processed {processed_files} files, generated dependency graph, and analyzed project structure."

    def _get_all_files(self, directory_content: Dict[str, str]) -> Dict[str, str]:
        all_files = {}
        for path, content in directory_content.items():
            if os.path.isdir(path):
                # If it's a directory, recursively get all files
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            all_files[file_path] = f.read()
            else:
                # If it's a file, add it directly
                all_files[path] = content
        return all_files

    def _analyze_java_project_structure(self, all_files: Dict[str, str]) -> Dict:
        java_files = [file for file in all_files.keys() if file.endswith('.java')]
        project_analysis = {
            "file_count": len(all_files),
            "java_file_count": len(java_files),
            "packages": list(set([os.path.dirname(file) for file in java_files])),
            "source_files": [file for file in java_files if "/src/main/" in file],
            "test_files": [file for file in java_files if "/src/test/" in file],
            "config_files": [file for file in all_files.keys() if file.endswith(('.xml', '.properties', '.yml', '.yaml'))],
            "sonar_config": self._parse_sonar_config(all_files)
        }
        return project_analysis

    def _parse_sonar_config(self, all_files: Dict[str, str]) -> Dict[str, str]:
        sonar_file = next((content for file, content in all_files.items() if 'sonar-project.properties' in file), None)
        if sonar_file:
            config = {}
            for line in sonar_file.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
            return config
        return {}

    def _upsert_document(self, doc):
        try:
            self.knowledge_base.vector_db.upsert([doc])
            logger.info(f"Upserted file {doc.name} to vector database")
        except AttributeError:
            try:
                self.knowledge_base.vector_db.insert([doc])
                logger.info(f"Inserted file {doc.name} to vector database")
            except IntegrityError:
                logger.warning(f"Document {doc.name} already exists in the database. Skipping insertion.")

    def _store_dependency_graph(self, project_name: str, dependency_graph: Dict, project_type: str):
        doc = Document(
            name=f"{project_name}_dependency_graph",
            content=json.dumps(dependency_graph, indent=2),
            meta_data={
                "project": project_name,
                "type": f"{project_type}_dependency_graph"
            }
        )
        self._upsert_document(doc)
        logger.info(f"Upserted dependency graph for project {project_name}")

    def _store_project_analysis(self, project_name: str, project_analysis: Dict, project_type: str):
        doc = Document(
            name=f"{project_name}_project_analysis",
            content=json.dumps(project_analysis, indent=2),
            meta_data={
                "project": project_name,
                "type": f"{project_type}_project_analysis"
            }
        )
        self._upsert_document(doc)
        logger.info(f"Upserted project analysis for project {project_name}")

    def analyze_project_structure(self, project_name: str, project_type: str) -> str:
        analysis_doc = self.knowledge_base.search(query=f"project:{project_name} type:{project_type}_project_analysis", num_documents=1)
        if analysis_doc:
            try:
                structure = json.loads(analysis_doc[0].content)
                return json.dumps(structure, indent=2)
            except json.JSONDecodeError:
                # If it's not JSON, return a formatted version of whatever is stored
                return json.dumps({"Warning": "Stored project analysis is not in JSON format", "Raw Content": analysis_doc[0].content}, indent=2)
        else:
            return json.dumps({"error": f"No project analysis found for {project_type} project '{project_name}'"}, indent=2)

    def find_component(self, project_name: str, component_name: str, project_type: str) -> str:
        namespace = self._get_namespace(project_name, project_type)
        files = self.knowledge_base.search(query=f"{component_name}", num_documents=5, namespace=namespace)
        
        results = []
        for file in files:
            if component_name.lower() in file.name.lower():
                results.append(f"Found in {file.name}:\n{file.content[:200]}...")
        
        return "\n\n".join(results) if results else f"Component {component_name} not found"

    def get_file_content(self, project_name: str, file_path: str, project_type: str) -> Optional[str]:
        files = self.knowledge_base.search(query=f"project:{project_name} type:{project_type}_file name:{file_path}", num_documents=1)
        return files[0].content if files else None

    def get_code_snippet(self, project_name: str, file_path: str, start_line: int, end_line: int, project_type: str) -> Optional[str]:
        content = self.get_file_content(project_name, file_path, project_type)
        if content:
            lines = content.split('\n')
            return '\n'.join(lines[start_line-1:end_line])
        return None

    def get_dependency_graph(self, project_name: str, project_type: str) -> Optional[Dict]:
        graph_doc = self.knowledge_base.search(query=f"project:{project_name} type:{project_type}_dependency_graph", num_documents=1)
        if graph_doc and graph_doc[0].content:
            try:
                return json.loads(graph_doc[0].content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse dependency graph JSON for project {project_name}")
                return None
        else:
            logger.warning(f"No dependency graph found for project {project_name}")
            return None
    
    def preprocess_query(query, current_project, current_project_type):
       return f"In the context of the {current_project_type} project '{current_project}': {query}"
   
    def add_context_reminder(messages, current_project, current_project_type):
        reminder = f"Remember, we are discussing the {current_project_type} project named '{current_project}'. Only use information relevant to this project."
        messages.append({"role": "system", "content": reminder})
        return messages
    
    def filter_results(results, current_project, current_project_type):
        return [r for r in results if r.meta_data.get('project') == current_project and r.meta_data.get('type').startswith(current_project_type)]
    
    def visualize_project_structure(self, project_name: str, project_type: str):
        project_info = self.analyze_project_structure(project_name, project_type)
        if not project_info:
            return "No project structure available"

        G = nx.DiGraph()
        def add_nodes(structure, parent=None):
            for key, value in structure.items():
                G.add_node(key)
                if parent:
                    G.add_edge(parent, key)
                if isinstance(value, dict):
                    add_nodes(value, key)

        add_nodes(json.loads(project_info)["package_structure"])

        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=3000, font_size=8, arrows=True)
        plt.title(f"Project Structure: {project_name}")
        plt.savefig(f"{project_name}_structure.png")
        plt.close()

        return f"Project structure visualization saved as {project_name}_structure.png"

    def generate_class_diagram(self, project_name: str, project_type: str):
        project_info = self.analyze_project_structure(project_name, project_type)
        if not project_info:
            return "No project information available"

        info = json.loads(project_info)
        
        dot = graphviz.Digraph(comment='Class Diagram')
        dot.attr(rankdir='TB', size='8,8')

        for file_info in info["files"]:
            if file_info.get("class_name"):
                dot.node(file_info["class_name"], shape='record', label='{' + file_info["class_name"] + '|' + 
                        '\\n'.join(file_info["fields"]) + '|' + '\\n'.join(file_info["methods"]) + '}')

        dot.render(f"{project_name}_class_diagram", format='png', cleanup=True)
        return f"Class diagram generated and saved as {project_name}_class_diagram.png"

    def visualize_dependency_graph(self, project_name: str, project_type: str):
        dependency_graph = self.get_dependency_graph(project_name, project_type)
        if not dependency_graph:
            return "No dependency graph available"

        G = nx.DiGraph()
        for dep, info in dependency_graph.items():
            G.add_node(dep)
            if isinstance(info, dict) and "dependencies" in info:
                for sub_dep in info["dependencies"]:
                    G.add_edge(dep, sub_dep)

        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_color='lightgreen', node_size=3000, font_size=8, arrows=True)
        plt.title(f"Dependency Graph: {project_name}")
        plt.savefig(f"{project_name}_dependencies.png")
        plt.close()

        return f"Dependency graph visualization saved as {project_name}_dependencies.png"

    def generate_project_summary(self, project_name: str, project_type: str):
        project_info = self.analyze_project_structure(project_name, project_type)
        dependency_graph = self.get_dependency_graph(project_name, project_type)

        if not project_info:
            return "No project information available"

        info = json.loads(project_info)
        
        summary = f"Project Summary for {project_name} ({project_type})\n\n"
        summary += f"Total Files: {len(info.get('files', []))}\n"
        summary += f"Classes: {len(info.get('classes', []))}\n"
        summary += f"Interfaces: {len(info.get('interfaces', []))}\n"
        summary += f"Enums: {len(info.get('enums', []))}\n\n"
        
        if dependency_graph:
            summary += "Key Dependencies:\n"
            for dep, version in list(dependency_graph.items())[:10]:  # Show top 10 dependencies
                summary += f"- {dep}: {version}\n"
        else:
            summary += "No dependency information available.\n"
        
        return summary

    def visualize_project(self, project_name: str, project_type: str):
        structure_result = self.visualize_project_structure(project_name, project_type)
        class_diagram_result = self.generate_class_diagram(project_name, project_type)
        dependency_result = self.visualize_dependency_graph(project_name, project_type)
        summary = self.generate_project_summary(project_name, project_type)

        return f"{structure_result}\n{class_diagram_result}\n{dependency_result}\n\nProject Summary:\n{summary}"
