import pytest
import os
import json
from pathlib import Path
import networkx as nx
from core.models import GraphModel, FileNode, Dependency, AnalysisResult, ParsingReport
from architecture.analyzer import ArchitectureAnalysis, Metrics, Hotspot, RoleClassification
from architecture.rules import RuleViolation
from reports.markdown import MarkdownReporter
from reports.json_exporter import JSONExporter
from reports.graphviz import GraphvizReporter
from reports.html_reporter import HTMLReporter
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
        analysis_state="complete",
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
    
    result = AnalysisResult(
        graph=domain_model,
        analysis=analysis,
        parsing_report=ParsingReport()
    )
    
    return result, nx_graph

def test_markdown_reporter(tmp_path, dummy_data):
    """A, B, C. Markdown report generation."""
    result, nx_graph = dummy_data
    out_dir = tmp_path / ".docswarm"
    
    path = MarkdownReporter.render(result.graph, result.analysis, str(out_dir))
    
    assert os.path.exists(path)
    content = Path(path).read_text(encoding="utf-8")
    assert "85/100" in content
    assert "R1" in content
    assert "Hotspots" in content

def test_json_exporter(tmp_path, dummy_data):
    """D, E. JSON export generation."""
    result, nx_graph = dummy_data
    out_dir = tmp_path / ".docswarm"
    
    path = JSONExporter.export(result, str(out_dir))
    
    assert os.path.exists(path)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    
    assert data["artifact_schema_version"] == "1.1"
    assert data["analysis_state"] == "complete"
    assert data["docswarm_version"] == "0.2.0"
    
    # Prove the exact legacy graph structure is intact
    assert "nodes" in data["graph"]
    assert data["graph"]["nodes"]["A"]["role"] == "Controller"
    assert data["graph"]["nodes"]["A"]["dependencies"][0]["target_id"] == "B"
    assert data["graph"]["nodes"]["A"]["dependencies"][1]["target_id"] == "ext"
    
    # Prove the exact legacy analysis structure is intact
    assert data["analysis"]["health_score"] == 85
    assert data["analysis"]["metrics"]["num_nodes"] == 2
    assert data["analysis"]["hotspots"][0]["node"] == "B"
    assert data["analysis"]["role_classifications"]["A"]["confidence"] == "high"
    assert data["analysis"]["violations"][0]["rule_id"] == "R1"
    
    # Prove nothing was unexpectedly removed or structurally altered
    assert set(data["analysis"].keys()) == {"health_score", "analysis_state", "metrics", "cycles", "hotspots", "role_classifications", "violations"}

def test_graphviz_dot_export(tmp_path, dummy_data):
    """F, I. DOT export and internal edges only."""
    result, nx_graph = dummy_data
    out_dir = tmp_path / ".docswarm"
    
    path = GraphvizReporter.export_dot(result.graph, result.analysis, str(out_dir))
    
    assert os.path.exists(path)
    content = Path(path).read_text(encoding="utf-8")
    
    # Internal edge A -> B is in DOT
    assert '"A" -> "B"' in content or 'A -> B' in content or '"A" -> "B";' in content
    # External edge 'ext' is NOT in DOT
    assert "ext" not in content

def test_graphviz_svg_success(tmp_path, dummy_data):
    """G. SVG rendering success."""
    result, nx_graph = dummy_data
    out_dir = tmp_path / ".docswarm"
    dot_path = GraphvizReporter.export_dot(result.graph, result.analysis, str(out_dir))
    
    # We rely on system 'dot' being available as verified in prerequisite.
    svg_path = GraphvizReporter.render_svg(dot_path, str(out_dir))
    assert os.path.exists(svg_path)

def test_graphviz_svg_failure(tmp_path, dummy_data):
    """H. SVG rendering failure when Graphviz missing."""
    result, nx_graph = dummy_data
    out_dir = tmp_path / ".docswarm"
    dot_path = GraphvizReporter.export_dot(result.graph, result.analysis, str(out_dir))
    
    with mock.patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="Graphviz 'dot' executable not found"):
            GraphvizReporter.render_svg(dot_path, str(out_dir))

def test_determinism(tmp_path, dummy_data):
    """J. Repeated rendering produces deterministic output."""
    result1, nx_graph1 = dummy_data
    
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
        analysis_state="complete",
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
    
    result2 = AnalysisResult(
        graph=domain_model2,
        analysis=analysis2,
        parsing_report=ParsingReport()
    )
    
    out_dir = tmp_path / ".docswarm"
    
    path1 = JSONExporter.export(result1, str(out_dir))
    content1 = Path(path1).read_bytes()
    
    path2 = JSONExporter.export(result2, str(out_dir))
    content2 = Path(path2).read_bytes()
    
    assert content1 == content2

def test_html_portability_and_security(tmp_path, dummy_data):
    result, _ = dummy_data
    
    # Inject XSS payload
    malicious_name = "</script><script>alert(1)</script>"
    result.graph.nodes["A"].name = malicious_name
    
    out_dir = tmp_path / ".docswarm"
    path = HTMLReporter.export(result, str(out_dir))
    
    content = Path(path).read_text(encoding="utf-8")
    
    # 1. Portability Assertions
    assert "src=" not in content, "Found potential external scripts"
    assert "<link " not in content, "Found potential external stylesheets"
    assert "http://" not in content, "Found unencrypted network requests"
    assert "https://" not in content, "Found external network requests"
    assert "cdn." not in content, "Found CDN references"
    
    # 2. XSS Protection Assertions
    assert malicious_name not in content, "Malicious payload was unescaped in HTML"
    assert "\\u003c/script\\u003e" in content, "Payload was not correctly escaped"
    
    # 3. Validation: Proof that parsing the JSON reconstructs perfectly
    # Find the JSON payload inside <script id="docswarm-data" type="application/json">
    import re
    match = re.search(r'<script id="docswarm-data" type="application/json">(.*?)</script>', content, re.DOTALL)
    assert match is not None
    json_payload = match.group(1)
    
    # Prove it parses
    parsed_data = json.loads(json_payload)
    assert parsed_data["graph"]["nodes"]["A"]["name"] == malicious_name
