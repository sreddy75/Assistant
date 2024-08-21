# java_utils.py

import xml.etree.ElementTree as ET
import re
import logging
import requests
from urllib.parse import urlparse
import javalang

logger = logging.getLogger(__name__)

def parse_pom_xml(pom_content):
    try:
        root = ET.fromstring(pom_content)
        dependencies = root.findall(".//dependency")
        return {f"{dep.find('groupId').text}:{dep.find('artifactId').text}": dep.find('version').text for dep in dependencies}
    except ET.ParseError as e:
        logger.error(f"Error parsing pom.xml: {e}")
        return {}

def parse_build_gradle(gradle_content):
    dependencies = {}
    dependency_pattern = re.compile(r'(\w+)\s*[\'\"](.+?):(.+?):(.+?)[\'\"]')
    
    for line in gradle_content.split('\n'):
        match = dependency_pattern.search(line)
        if match:
            scope, group, artifact, version = match.groups()
            dependencies[f"{group}:{artifact}"] = version
    
    return dependencies

def fetch_pom(group_id, artifact_id, version):
    base_url = "https://repo1.maven.org/maven2"
    group_path = group_id.replace('.', '/')
    pom_url = f"{base_url}/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
    
    try:
        response = requests.get(pom_url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error fetching POM for {group_id}:{artifact_id}:{version}: {e}")
        return None

def resolve_transitive_dependencies(dependency, resolved=None, depth=0, max_depth=5):
    if resolved is None:
        resolved = {}
    
    if depth > max_depth:
        return resolved

    group_id, artifact_id = dependency.split(':')
    version = resolved.get(dependency)
    
    if version is None:
        return resolved

    pom_content = fetch_pom(group_id, artifact_id, version)
    if pom_content is None:
        return resolved

    dependencies = parse_pom_xml(pom_content)
    resolved[dependency] = {
        "version": version,
        "dependencies": list(dependencies.keys())
    }

    for dep, ver in dependencies.items():
        if dep not in resolved:
            resolved[dep] = ver
            resolve_transitive_dependencies(dep, resolved, depth + 1, max_depth)

    return resolved

def generate_java_dependency_graph(pom_xml=None, build_gradle=None):
    dependencies = {}
    
    if pom_xml:
        dependencies.update(parse_pom_xml(pom_xml))
    
    if build_gradle:
        dependencies.update(parse_build_gradle(build_gradle))
    
    resolved_dependencies = {}
    for dep, version in dependencies.items():
        resolved_dependencies[dep] = version
        resolve_transitive_dependencies(dep, resolved_dependencies)

    return resolved_dependencies

def analyze_java_file(file_content):
    try:
        tree = javalang.parse.parse(file_content)
        
        info = {
            "imports": [],
            "class_name": None,
            "methods": [],
            "fields": []
        }
        
        for path, node in tree.filter(javalang.tree.ImportDeclaration):
            info["imports"].append(node.path)
        
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            info["class_name"] = node.name
            break  # Assuming we're interested in the first class declaration
        
        for path, node in tree.filter(javalang.tree.MethodDeclaration):
            info["methods"].append(node.name)
        
        for path, node in tree.filter(javalang.tree.FieldDeclaration):
            for declarator in node.declarators:
                info["fields"].append(declarator.name)
        
        return info
    except javalang.parser.JavaSyntaxError as e:
        print(f"JavaSyntaxError: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error analyzing Java file: {e}")
        return None

def get_java_project_structure(files):
    structure = {}
    for file_path in files:
        parts = file_path.split('/')
        current = structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = "file"
    
    return structure

def analyze_java_project(project_files):
    project_info = {
        "files": [],
        "classes": [],
        "interfaces": [],
        "enums": [],
        "package_structure": get_java_project_structure(project_files.keys()),
    }
    
    for file_path, content in project_files.items():
        file_info = analyze_java_file(content)
        if file_info is not None:
            file_info["path"] = file_path
            project_info["files"].append(file_info)
            
            if file_info["class_name"]:
                if "interface" in content:
                    project_info["interfaces"].append(file_info["class_name"])
                elif "enum" in content:
                    project_info["enums"].append(file_info["class_name"])
                else:
                    project_info["classes"].append(file_info["class_name"])
        else:
            # Handle the case where analyze_java_file returns None
            print(f"Warning: Could not analyze file {file_path}")
            project_info["files"].append({"path": file_path, "error": "Could not analyze file"})
    
    return project_info