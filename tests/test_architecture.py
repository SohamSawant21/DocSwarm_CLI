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
            
    analyzer.rule_engine = EvilRuleEngine(analyzer.config.rules)
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
    from core.config import DocSwarmConfig
    classifier = RoleClassifier(DocSwarmConfig().roles)
    
    f1 = FileNode(id="UserController.ts", path="UserController.ts", name="UserController.ts")
    r1 = classifier.classify(f1)
    assert r1.role == "Controller"
    assert "matches pattern" in r1.reason
    
    f2 = FileNode(id="UserService.ts", path="UserService.ts", name="UserService.ts")
    r2 = classifier.classify(f2)
    assert r2.role == "Service"
    assert r2.confidence == "suspected"
    
    f3 = FileNode(id="UserRepository.ts", path="UserRepository.ts", name="UserRepository.ts")
    r3 = classifier.classify(f3)
    assert r3.role == "Repository"
    
    f4 = FileNode(id="unknown.py", path="unknown.py", name="unknown.py")
    r4 = classifier.classify(f4)
    assert r4.role == "Unknown"
    assert r4.confidence == "none"

    # Verify overlapping priority
    r5 = classifier.classify(FileNode(id="UserService.tsx", path="UserService.tsx", name="UserService.tsx"))
    assert r5.role == "Service"
    
    r6 = classifier.classify(FileNode(id="UserController.tsx", path="UserController.tsx", name="UserController.tsx"))
    assert r6.role == "Controller"
    
    r7 = classifier.classify(FileNode(id="UserRepository.tsx", path="UserRepository.tsx", name="UserRepository.tsx"))
    assert r7.role == "Repository"
    
    r8 = classifier.classify(FileNode(id="UserModel.tsx", path="UserModel.tsx", name="UserModel.tsx"))
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

def test_custom_role_patterns_and_precedence():
    from core.config import DocSwarmConfig, RoleConfig
    config = DocSwarmConfig(
        roles=[
            # A completely custom role that will preempt due to ordering
            RoleConfig(role_name="GodObject", patterns=["*god*"]),
            # Redefine Model to only match exactly models.py
            RoleConfig(role_name="Model", patterns=["models.py"])
        ]
    )
    
    analyzer = ArchitectureAnalyzer(GraphModel(), nx.DiGraph(), config)
    classifier = analyzer.role_classifier
    
    # Custom pattern matches
    r1 = classifier.classify(FileNode(id="god.py", path="god.py", name="god.py"))
    assert r1.role == "GodObject"
    
    # Overlapping precedence: god object is defined first
    r2 = classifier.classify(FileNode(id="god_models.py", path="god_models.py", name="god_models.py"))
    assert r2.role == "GodObject"
    
    # Specific model matches
    r3 = classifier.classify(FileNode(id="models.py", path="models.py", name="models.py"))
    assert r3.role == "Model"
    
    # Fallback to unknown since default patterns are wiped
    r4 = classifier.classify(FileNode(id="controller.py", path="controller.py", name="controller.py"))
    assert r4.role == "Unknown"

def test_custom_rules_and_penalties():
    from core.config import DocSwarmConfig, RuleConfig, RoleConfig
    
    config = DocSwarmConfig(
        roles=[
            RoleConfig(role_name="GodObject", patterns=["god*"]),
            RoleConfig(role_name="Service", patterns=["service*"])
        ],
        rules=[
            RuleConfig(
                id="CUSTOM-001",
                source_role="GodObject",
                forbidden_target_role="Service",
                severity="critical",
                penalty=50,
                message="No."
            )
        ]
    )
    
    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from([("god.py", "service.py")])
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(id="god.py", path="god.py", name="god.py"))
    domain_model.add_node(FileNode(id="service.py", path="service.py", name="service.py"))
    
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph, config)
    result = analyzer.analyze()
    
    assert len(result.violations) == 1
    assert result.violations[0].rule_id == "CUSTOM-001"
    assert result.violations[0].penalty == 50
    assert result.health_score == 50

def test_structural_cycle_independent_of_declarative_rules():
    from core.config import DocSwarmConfig
    
    # Wipe all declarative rules
    config = DocSwarmConfig(rules=[])
    
    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from([("A", "B"), ("B", "A")])
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(id="A", path="A", name="A"))
    domain_model.add_node(FileNode(id="B", path="B", name="B"))
    
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph, config)
    result = analyzer.analyze()
    
    # Structural rule still fires
    assert len(result.violations) == 1
    assert result.violations[0].rule_id == "ARCH-001"
    assert result.violations[0].penalty == 15
    assert result.health_score == 85

def test_invalid_rule_configuration_validation():
    from core.config import RuleConfig
    from pydantic import ValidationError
    
    # Negative penalty
    with pytest.raises(ValidationError):
        RuleConfig(id="A", source_role="A", forbidden_target_role="B", severity="low", penalty=-1, message="")
        
    # Invalid severity
    with pytest.raises(ValidationError):
        RuleConfig(id="A", source_role="A", forbidden_target_role="B", severity="invalid", penalty=5, message="")

    # Empty identifier
    with pytest.raises(ValidationError):
        RuleConfig(id="", source_role="A", forbidden_target_role="B", severity="low", penalty=5, message="")

def test_determinism_repeated_analysis():
    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from([("A", "B"), ("B", "A")])
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(id="A", path="A", name="A"))
    domain_model.add_node(FileNode(id="B", path="B", name="B"))
    
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph)
    result1 = analyzer.analyze()
    result2 = analyzer.analyze()
    
    assert result1.health_score == result2.health_score
    assert len(result1.violations) == len(result2.violations)
    assert result1.metrics.num_cycles == result2.metrics.num_cycles

def test_fnmatch_semantic_boundaries():
    """Verify explicit fnmatch boundaries and case-insensitive behavior for RoleClassifier."""
    from core.config import DocSwarmConfig
    classifier = RoleClassifier(DocSwarmConfig().roles)
    
    # 1. Substring-equivalent patterns
    assert classifier.classify(FileNode(id="UserController.py", path="UserController.py", name="UserController.py")).role == "Controller"
    assert classifier.classify(FileNode(id="MyControllerFactory.py", path="MyControllerFactory.py", name="MyControllerFactory.py")).role == "Controller"
    assert classifier.classify(FileNode(id="src/api/controller.py", path="src/api/controller.py", name="controller.py")).role == "Controller"
    
    # 2. Path patterns
    # Verify that `*models/*` matches across nested structures due to fnmatch cross-directory semantics
    assert classifier.classify(FileNode(id="models/User.py", path="models/User.py", name="User.py")).role == "Model"
    assert classifier.classify(FileNode(id="models/nested/User.py", path="models/nested/User.py", name="User.py")).role == "Model"
    assert classifier.classify(FileNode(id="src/models/User.py", path="src/models/User.py", name="User.py")).role == "Model"
    
    # 3 & 4. Case sensitivity and Filename vs Path matching
    assert classifier.classify(FileNode(id="UserService.py", path="UserService.py", name="UserService.py")).role == "Service"
    assert classifier.classify(FileNode(id="userservice.py", path="userservice.py", name="userservice.py")).role == "Service"
    assert classifier.classify(FileNode(id="src/SERVICE/User.py", path="src/SERVICE/User.py", name="User.py")).role == "Service"
    
    # 6. Unknown fall-through
    assert classifier.classify(FileNode(id="unknown.py", path="unknown.py", name="unknown.py")).role == "Unknown"

def test_multiple_violations_accumulation_and_floor():
    """Verify health score accumulation determinism and floor logic."""
    from core.config import DocSwarmConfig, RuleConfig, RoleConfig
    config = DocSwarmConfig(
        roles=[
            RoleConfig(role_name="A", patterns=["a.py"]),
            RoleConfig(role_name="B", patterns=["b.py"]),
            RoleConfig(role_name="C", patterns=["c.py"])
        ],
        rules=[
            RuleConfig(id="R1", source_role="A", forbidden_target_role="B", severity="low", penalty=20, message=""),
            RuleConfig(id="R2", source_role="B", forbidden_target_role="C", severity="medium", penalty=90, message="")
        ]
    )
    
    nx_graph = nx.DiGraph()
    # Edges are inherently ordered by insertion in modern networkx
    nx_graph.add_edges_from([("a.py", "b.py"), ("b.py", "c.py")])
    
    domain_model = GraphModel()
    domain_model.add_node(FileNode(id="a.py", path="a.py", name="a.py"))
    domain_model.add_node(FileNode(id="b.py", path="b.py", name="b.py"))
    domain_model.add_node(FileNode(id="c.py", path="c.py", name="c.py"))
    
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph, config)
    result = analyzer.analyze()
    
    # Two violations should be accumulated deterministically
    assert len(result.violations) == 2
    assert result.violations[0].rule_id == "R1"
    assert result.violations[1].rule_id == "R2"
    
    # Total penalty = 110, Health score = max(0, 100 - 110) = 0
    assert result.health_score == 0

def test_deterministic_cycle_bounding():
    """Verify that DocSwarm consumes at most 100 yielded cycles and sets analysis_state='bounded'."""
    from core.config import DocSwarmConfig
    
    # Create a complete graph with >=100 cycles
    # A complete digraph with 6 nodes has 409 cycles, which exceeds our 100 budget
    nx_graph = nx.relabel_nodes(nx.complete_graph(6, create_using=nx.DiGraph()), lambda x: f"node_{x}")
    
    domain_model = GraphModel()
    for i in range(6):
        node_id = f"node_{i}"
        domain_model.add_node(FileNode(id=node_id, path=node_id, name=node_id))
        
    # Test boundary where >100 exist
    analyzer = ArchitectureAnalyzer(domain_model, nx_graph, DocSwarmConfig())
    result = analyzer.analyze()
    
    # Create identical graph but shuffle insertion order
    import random
    edges = list(nx_graph.edges())
    random.seed(42)
    random.shuffle(edges)
    
    nx_graph_shuffled = nx.DiGraph()
    nx_graph_shuffled.add_nodes_from(reversed(list(nx_graph.nodes())))
    nx_graph_shuffled.add_edges_from(edges)
    
    domain_model_shuffled = GraphModel()
    for node_id in reversed(list(nx_graph.nodes())):
        domain_model_shuffled.add_node(FileNode(id=node_id, path=node_id, name=node_id))
        
    analyzer_shuffled = ArchitectureAnalyzer(domain_model_shuffled, nx_graph_shuffled, DocSwarmConfig())
    result_shuffled = analyzer_shuffled.analyze()
    
    # Verify deterministic output (both cycles bounded at 100 and identical)
    assert len(result.cycles) == 100
    assert result.analysis_state == "bounded"
    
    assert len(result_shuffled.cycles) == 100
    assert result_shuffled.analysis_state == "bounded"
    
    # Prove exact identity of the list of cycles (they are lists of strings)
    assert result.cycles == result_shuffled.cycles
    
    # ARCH-001 penalty applies exactly once
    cycle_violations = [v for v in result.violations if v.rule_id == "ARCH-001"]
    assert len(cycle_violations) == 1
    assert cycle_violations[0].penalty == 15
    
    # Test where <100 exist
    nx_graph_small = nx.relabel_nodes(nx.complete_graph(3, create_using=nx.DiGraph()), lambda x: f"node_{x}") # 5 cycles
    domain_model_small = GraphModel()
    for i in range(3):
        node_id = f"node_{i}"
        domain_model_small.add_node(FileNode(id=node_id, path=node_id, name=node_id))
        
    analyzer_small = ArchitectureAnalyzer(domain_model_small, nx_graph_small, DocSwarmConfig())
    result_small = analyzer_small.analyze()
    
    assert len(result_small.cycles) == 5
    assert result_small.analysis_state == "complete"
