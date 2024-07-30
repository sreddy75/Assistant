import os
import json
import subprocess
import streamlit as st

# Function to call Node.js script and build dependency graph
def build_dependency_graph(project_dir):
    result = subprocess.run(['node', 'parse.js', project_dir], capture_output=True, text=True)
    return json.loads(result.stdout)

def save_dependency_graph(graph, output_path):
    with open(output_path, 'w') as file:
        json.dump(graph, file, indent=2)

def load_dependency_graph(output_path):
    if os.path.exists(output_path):
        with open(output_path, 'r') as file:
            return json.load(file)
    return {}

# Streamlit UI
st.title("React Project Dependency Graph")

project_dir = st.text_input("Enter the path to your React project directory:")
output_path = 'dependency_graph.json'

if st.button("Build Dependency Graph"):
    if project_dir:
        dependency_graph = build_dependency_graph(project_dir)
        save_dependency_graph(dependency_graph, output_path)
        st.success("Dependency graph built and saved successfully.")
    else:
        st.error("Please enter a valid project directory path.")

# Load the dependency graph for visualization
dependency_graph = load_dependency_graph(output_path)

def display_graph(graph):
    for file, deps in graph.items():
        st.write(f"**{file}**")
        for dep in deps:
            st.write(f"  - {dep}")

display_graph(dependency_graph)

# Function to find dependencies of a specific file
def find_dependencies(file_path, graph):
    if file_path in graph:
        return graph[file_path]
    return []

file_path = st.text_input("Enter file path to see its dependencies:")
if file_path:
    dependencies = find_dependencies(file_path, dependency_graph)
    st.write(f"Dependencies of **{file_path}**:")
    for dep in dependencies:
        st.write(f"  - {dep}")