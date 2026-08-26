import pytest
import os
import json
from pathlib import Path
import networkx as nx
from core.models import GraphModel, FileNode, Dependency
from architecture.analyzer import ArchitectureAnalysis, Metrics, Hotspot, RoleClassification
from architecture.rules import RuleViolation
from reports.markdown import MarkdownReporter
from reports.json_exporter import JSONExporter
from reports.graphviz import GraphvizReporter
from unittest import mock
import subprocess

@pytest.fixture
def dummy_data():
    nx_graph = nx.DiGraph()
    nx_graph.add_node("A", role="Controller")
    nx_graph.add_node("B", role="Service")
    nx_graph.add_edge("A", "B")
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(
        id="A", path="A", name="A", role="Controller", 
        dependencies=[
            Dependency(target_id="B", type="import"),
            Dependency(target_id="ext", type="external")
        ]
    ))
    domain_model.add_node(FileNode(id="B", path="B", name="B", role="Service"))
    
    analysis = ArchitectureAnalysis(
        health_score=85,
        metrics=Metrics(num_nodes=2, num_edges=1, num_cycles=0, fan_in={"B": 1}, fan_out={"A": 1}),
        cycles=[],
        hotspots=[Hotspot(node="B", metric="fan_in", value=1, reason="reason")],
        role_classifications={"A": RoleClassification(role="Controller", confidence="high", reason="r")},
        violations=[
            RuleViolation(
                rule_id="R1", severity="high", message="m", penalty=15,
                affected_files=["A"], status="confirmed", reason="r"
            )
        ]
    )
    
    return domain_model, nx_graph, analysis

def test_markdown_reporter(tmp_path, dummy_data):
    """A, B, C. Markdown report generation."""
    domain_model, nx_graph, analysis = dummy_data
    out_dir = tmp_path / ".docswarm"
    
    path = MarkdownReporter.render(domain_model, analysis, str(out_dir))
    
    assert os.path.exists(path)
    content = Path(path).read_text(encoding="utf-8")
    assert "85/100" in content
    assert "R1" in content
    assert "Hotspots" in content

def test_json_exporter(tmp_path, dummy_data):
    """D, E. JSON export generation."""
    domain_model, nx_graph, analysis = dummy_data
    out_dir = tmp_path / ".docswarm"
    
    path = JSONExporter.export(domain_model, analysis, str(out_dir))
    
    assert os.path.exists(path)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    
    assert "A" in data["graph"]["nodes"]
    # Check that external dep is kept in GraphModel JSON but NOT nx_graph edges
    assert data["graph"]["nodes"]["A"]["dependencies"][1]["target_id"] == "ext"
    assert data["analysis"]["health_score"] == 85

def test_graphviz_dot_export(tmp_path, dummy_data):
    """F, I. DOT export and internal edges only."""
    domain_model, nx_graph, analysis = dummy_data
    out_dir = tmp_path / ".docswarm"
    
    path = GraphvizReporter.export_dot(domain_model, analysis, str(out_dir))
    
    assert os.path.exists(path)
    content = Path(path).read_text(encoding="utf-8")
    
    # Internal edge A -> B is in DOT
    assert '"A" -> "B"' in content or 'A -> B' in content or '"A" -> "B";' in content
    # External edge 'ext' is NOT in DOT
    assert "ext" not in content

def test_graphviz_svg_success(tmp_path, dummy_data):
    """G. SVG rendering success."""
    domain_model, nx_graph, analysis = dummy_data
    out_dir = tmp_path / ".docswarm"
    dot_path = GraphvizReporter.export_dot(domain_model, analysis, str(out_dir))
    
    # We rely on system 'dot' being available as verified in prerequisite.
    svg_path = GraphvizReporter.render_svg(dot_path, str(out_dir))
    assert os.path.exists(svg_path)

def test_graphviz_svg_failure(tmp_path, dummy_data):
    """H. SVG rendering failure when Graphviz missing."""
    domain_model, nx_graph, analysis = dummy_data
    out_dir = tmp_path / ".docswarm"
    dot_path = GraphvizReporter.export_dot(domain_model, analysis, str(out_dir))
    
    with mock.patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="Graphviz 'dot' executable not found"):
            GraphvizReporter.render_svg(dot_path, str(out_dir))

def test_determinism(tmp_path, dummy_data):
    """J. Repeated rendering produces deterministic output."""
    domain_model1, nx_graph1, analysis1 = dummy_data
    
    # Create identical data but constructed in different insertion orders
    domain_model2 = GraphModel()
    domain_model2.add_node(FileNode(id="B", path="B", name="B", role="Service")) # B first instead of A
    domain_model2.add_node(FileNode(
        id="A", path="A", name="A", role="Controller", 
        dependencies=[
            Dependency(target_id="ext", type="external"), # Ext first instead of B
            Dependency(target_id="B", type="import")
        ]
    ))
    
    analysis2 = ArchitectureAnalysis(
        health_score=85,
        metrics=Metrics(num_nodes=2, num_edges=1, num_cycles=0, fan_in={"B": 1}, fan_out={"A": 1}),
        cycles=[],
        hotspots=[Hotspot(node="B", metric="fan_in", value=1, reason="reason")],
        role_classifications={"A": RoleClassification(role="Controller", confidence="high", reason="r")},
        violations=[
            RuleViolation(
                rule_id="R1", severity="high", message="m", penalty=15,
                affected_files=["A"], status="confirmed", reason="r"
            )
        ]
    )
    
    out_dir = tmp_path / ".docswarm"
    
    path1 = JSONExporter.export(domain_model1, analysis1, str(out_dir))
    content1 = Path(path1).read_bytes()
    
    # Rename file so we don't just overwrite and can compare side-by-side if needed
    path2 = JSONExporter.export(domain_model2, analysis2, str(out_dir))
    # It will overwrite graph.json. So we need to read it again.
    content2 = Path(path2).read_bytes()
    
    assert content1 == content2
