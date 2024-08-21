# npm_utils.py

import subprocess
import json

def run_npm_command(command, cwd=None):
    try:
        result = subprocess.run(["npm"] + command.split(), cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running npm command: {e}")
        return None

def get_dependency_versions(package_json):
    dependencies = package_json.get("dependencies", {})
    dev_dependencies = package_json.get("devDependencies", {})
    all_dependencies = {**dependencies, **dev_dependencies}
    
    versions = {}
    for package, version_range in all_dependencies.items():
        available_versions = run_npm_command(f"view {package} versions --json")
        if available_versions:
            available_versions = json.loads(available_versions)
            max_version = max_satisfying(available_versions, version_range)
            versions[package] = max_version
    
    return versions

def generate_dependency_graph(package_json):
    versions = get_dependency_versions(package_json)
    graph = {}
    for package, version in versions.items():
        dependencies = run_npm_command(f"view {package}@{version} dependencies --json")
        if dependencies:
            graph[package] = json.loads(dependencies)
    return graph