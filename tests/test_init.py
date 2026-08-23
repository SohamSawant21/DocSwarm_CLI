import pytest
from core.models import FileNode, GraphModel, Dependency
from graph.builder import GraphBuilder
from detectors.roles import classify_role
from analyzers.blueprint import BlueprintGenerator
import networkx as nx

def test_project_initialization():
    """Verify that the core domain models can be instantiated."""
    node = FileNode(
        id="src/main.py",
        path="/absolute/path/src/main.py",
        name="main.py"
    )
    
    assert node.id == "src/main.py"
    assert node.role == "Other"
    
    # Test role classification
    role = classify_role(node.path)
    assert role == "Entry Points"
    node.role = role

    graph_model = GraphModel()
    graph_model.add_node(node)
    
    assert len(graph_model.nodes) == 1
    assert "src/main.py" in graph_model.nodes
    assert graph_model.nodes["src/main.py"].role == "Entry Points"

def test_graph_builder():
    """Verify that the NetworkX graph builder adapter works."""
    builder = GraphBuilder()
    f1 = FileNode(id="src/main.py", path="src/main.py", name="main.py", dependencies=[Dependency(target_id="src/utils.py", type="import")])
    f2 = FileNode(id="src/utils.py", path="src/utils.py", name="utils.py")
    builder.build([f1, f2])
    
    assert builder.nx_graph.has_edge("src/main.py", "src/utils.py")

def test_blueprint_generator():
    """Verify blueprint generation basic layout."""
    graph_model = GraphModel()
    graph_model.add_node(FileNode(id="src/main.py", path="src/main.py", name="main.py", role="Entry Points"))
    
    nx_graph = nx.DiGraph()
    nx_graph.add_node("src/main.py")
    
    blueprint = BlueprintGenerator.generate_repo_map(graph_model, nx_graph)
    assert "### REPOSITORY ARCHITECTURE BLUEPRINT" in blueprint
    assert "Entry Points" in blueprint
    assert "src/main.py" in blueprint
