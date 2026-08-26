from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field
import networkx as nx
from core.models import GraphModel, FileNode
from .rules import RuleEngine, RuleViolation

class RoleClassification(BaseModel):
    role: str
    confidence: str
    reason: str

class Hotspot(BaseModel):
    node: str
    metric: str
    value: float
    reason: str

class Metrics(BaseModel):
    num_nodes: int
    num_edges: int
    num_cycles: int
    fan_in: Dict[str, int]
    fan_out: Dict[str, int]

class ArchitectureAnalysis(BaseModel):
    health_score: int
    metrics: Metrics
    cycles: List[List[str]]
    hotspots: List[Hotspot]
    role_classifications: Dict[str, RoleClassification]
    violations: List[RuleViolation]

import fnmatch
from core.config import RoleConfig, RuleConfig

class RoleClassifier:
    def __init__(self, roles: List[RoleConfig]):
        self.roles = roles

    def classify(self, node: FileNode) -> RoleClassification:
        # node.id is the stable relative path with forward slashes
        rel_path = node.id.lower()
        name_lower = node.name.lower()
        
        for role in self.roles:
            for pattern in role.patterns:
                pat_lower = pattern.lower()
                # Match against either the relative path or the bare filename
                if fnmatch.fnmatch(rel_path, pat_lower) or fnmatch.fnmatch(name_lower, pat_lower):
                    return RoleClassification(
                        role=role.role_name,
                        confidence="suspected",
                        reason=f"matches pattern '{pattern}'"
                    )
                    
        return RoleClassification(role="Unknown", confidence="none", reason="no pattern matched")

from core.config import DocSwarmConfig

class ArchitectureAnalyzer:
    def __init__(self, domain_model: GraphModel, nx_graph: nx.DiGraph, config: DocSwarmConfig | None = None):
        self.domain_model = domain_model
        self.nx_graph = nx_graph
        self.config = config or DocSwarmConfig()
        self.rule_engine = RuleEngine(self.config.rules)
        self.role_classifier = RoleClassifier(self.config.roles)
        
    def analyze(self) -> ArchitectureAnalysis:
        # 1. Base Metrics
        num_nodes = self.nx_graph.number_of_nodes()
        num_edges = self.nx_graph.number_of_edges()
        
        # Calculate cycles deterministically
        try:
            cycles = list(nx.simple_cycles(self.nx_graph))
        except Exception:
            cycles = []
            
        # 2. Fan-in / Fan-out
        fan_in_map = {n: d for n, d in self.nx_graph.in_degree()}
        fan_out_map = {n: d for n, d in self.nx_graph.out_degree()}
        
        metrics = Metrics(
            num_nodes=num_nodes,
            num_edges=num_edges,
            num_cycles=len(cycles),
            fan_in=fan_in_map,
            fan_out=fan_out_map
        )
        
        # 3. Role Classification
        roles = {}
        for node_id, node in self.domain_model.nodes.items():
            roles[node_id] = self.role_classifier.classify(node)
            
        # 4. Hotspots (Heuristic: fan-in >= 5 OR fan-out >= 7)
        hotspots = []
        for n, fin in fan_in_map.items():
            if fin >= 5:
                hotspots.append(Hotspot(node=n, metric="fan_in", value=fin, reason="High incoming dependency count (>= 5)"))
        for n, fout in fan_out_map.items():
            if fout >= 7:
                hotspots.append(Hotspot(node=n, metric="fan_out", value=fout, reason="High outgoing dependency count (>= 7)"))
                
        # 5. Rule Evaluation
        violations = self.rule_engine.evaluate(self.nx_graph, cycles, roles)
        
        # 6. Health Score Calculation
        total_penalty = sum(v.penalty for v in violations)
        final_score = max(0, 100 - total_penalty)
        
        return ArchitectureAnalysis(
            health_score=final_score,
            metrics=metrics,
            cycles=cycles,
            hotspots=hotspots,
            role_classifications=roles,
            violations=violations
        )
