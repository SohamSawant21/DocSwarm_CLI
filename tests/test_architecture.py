import pytest
import networkx as nx
from core.models import GraphModel, FileNode
from architecture.analyzer import ArchitectureAnalyzer, RoleClassifier
from architecture.rules import RuleEngine

def test_acyclic_graph():
    """A. Acyclic graph A->B->C."""
    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from([("A", "B"), ("B", "C")])
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(id="A", path="A", name="A"))
    domain_model.add_node(FileNode(id="B", path="B", name="B"))
    domain_model.add_node(FileNode(id="C", path="C", name="C"))
    
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph)
    result = analyzer.analyze()
    
    assert result.metrics.num_cycles == 0
    assert len(result.cycles) == 0

def test_circular_graph_and_health_score():
    """
    B. Circular graph A->B->C->A.
    C. Health score calculation.
    """
    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from([("A", "B"), ("B", "C"), ("C", "A")])
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(id="A", path="A", name="A"))
    domain_model.add_node(FileNode(id="B", path="B", name="B"))
    domain_model.add_node(FileNode(id="C", path="C", name="C"))
    
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph)
    result = analyzer.analyze()
    
    assert result.metrics.num_cycles > 0
    # The Circular dependency rule should fire
    cycle_violations = [v for v in result.violations if v.rule_id == "ARCH-001"]
    assert len(cycle_violations) == 1
    assert cycle_violations[0].penalty == 15
    assert result.health_score == 85
    assert cycle_violations[0].status == "confirmed"

def test_score_floor():
    """D. Score floor never below 0."""
    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from([("A", "B")])
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(id="A", path="A", name="A"))
    domain_model.add_node(FileNode(id="B", path="B", name="B"))
    
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph)
    
    # Force a massive penalty
    from architecture.rules import RuleViolation
    class EvilRuleEngine(RuleEngine):
        def evaluate(self, nx_graph, cycles, roles):
            return super().evaluate(nx_graph, cycles, roles) + [
                RuleViolation(rule_id='EVIL', severity='high', message='Evil', penalty=500, affected_files=[], status='suspected', reason='evil')
            ]
            
    analyzer.rule_engine = EvilRuleEngine()
    result = analyzer.analyze()
    
    assert result.health_score == 0

def test_fan_in_fan_out():
    """E. Fan-in. F. Fan-out."""
    nx_graph = nx.DiGraph()
    # A->C, B->C
    nx_graph.add_edges_from([("A", "C"), ("B", "C")])
    # A->B
    nx_graph.add_edges_from([("A", "B")])
    
    domain_model = GraphModel()
    for n in ["A", "B", "C"]:
        domain_model.add_node(FileNode(id=n, path=n, name=n))
        
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph)
    result = analyzer.analyze()
    
    assert result.metrics.fan_in["C"] == 2
    assert result.metrics.fan_out["A"] == 2

def test_hotspot_detection():
    """G. Hotspot detection (fan-in >= 5)."""
    nx_graph = nx.DiGraph()
    edges = [(f"Node{i}", "Target") for i in range(6)]
    nx_graph.add_edges_from(edges)
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(id="Target", path="Target", name="Target"))
    for i in range(6):
        domain_model.add_node(FileNode(id=f"Node{i}", path=f"Node{i}", name=f"Node{i}"))
        
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph)
    result = analyzer.analyze()
    
    hotspots = [h for h in result.hotspots if h.node == "Target"]
    assert len(hotspots) == 1
    assert hotspots[0].metric == "fan_in"
    assert hotspots[0].value == 6

def test_role_classification():
    """H. Role classification & I. Explanation."""
    f1 = FileNode(id="UserController.ts", path="UserController.ts", name="UserController.ts")
    r1 = RoleClassifier.classify(f1)
    assert r1.role == "Controller"
    assert "contains 'controller'" in r1.reason
    
    f2 = FileNode(id="UserService.ts", path="UserService.ts", name="UserService.ts")
    r2 = RoleClassifier.classify(f2)
    assert r2.role == "Service"
    assert r2.confidence == "suspected"
    
    f3 = FileNode(id="UserRepository.ts", path="UserRepository.ts", name="UserRepository.ts")
    r3 = RoleClassifier.classify(f3)
    assert r3.role == "Repository"
    
    f4 = FileNode(id="unknown.py", path="unknown.py", name="unknown.py")
    r4 = RoleClassifier.classify(f4)
    assert r4.role == "Unknown"
    assert r4.confidence == "none"

    # Verify overlapping priority
    r5 = RoleClassifier.classify(FileNode(id="UserService.tsx", path="UserService.tsx", name="UserService.tsx"))
    assert r5.role == "Service"
    
    r6 = RoleClassifier.classify(FileNode(id="UserController.tsx", path="UserController.tsx", name="UserController.tsx"))
    assert r6.role == "Controller"
    
    r7 = RoleClassifier.classify(FileNode(id="UserRepository.tsx", path="UserRepository.tsx", name="UserRepository.tsx"))
    assert r7.role == "Repository"
    
    r8 = RoleClassifier.classify(FileNode(id="UserModel.tsx", path="UserModel.tsx", name="UserModel.tsx"))
    assert r8.role == "Model"

def test_suspected_layer_violation():
    """J. Verify suspected layer violations are explicitly labeled 'suspected'."""
    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from([("model.py", "controller.py")])
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(id="model.py", path="model.py", name="model.py"))
    domain_model.add_node(FileNode(id="controller.py", path="controller.py", name="controller.py"))
    
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph)
    result = analyzer.analyze()
    
    violations = [v for v in result.violations if v.rule_id == "ARCH-002"]
    assert len(violations) == 1
    assert violations[0].status == "suspected"
    assert "Models typically should not depend on Controllers" in violations[0].reason

def test_graph_unchanged():
    """K. Verify graph is unchanged after analysis."""
    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from([("A", "B")])
    original_nodes = list(nx_graph.nodes)
    original_edges = list(nx_graph.edges)
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(id="A", path="A", name="A"))
    domain_model.add_node(FileNode(id="B", path="B", name="B"))
    
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph)
    analyzer.analyze()
    
    assert list(nx_graph.nodes) == original_nodes
    assert list(nx_graph.edges) == original_edges
