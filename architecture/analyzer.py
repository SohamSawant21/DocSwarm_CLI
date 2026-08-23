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

class RoleClassifier:
    @staticmethod
    def classify(node: FileNode) -> RoleClassification:
        name_lower = node.name.lower()
        path_lower = node.path.lower()
        
        # Deterministic heuristic mapping
        if "controller" in name_lower or "controller" in path_lower:
            return RoleClassification(role="Controller", confidence="suspected", reason="filename or path contains 'controller'")
        if "service" in name_lower or "service" in path_lower:
            return RoleClassification(role="Service", confidence="suspected", reason="filename or path contains 'service'")
        if "model" in name_lower or "entity" in name_lower or "models/" in path_lower:
            return RoleClassification(role="Model", confidence="suspected", reason="filename or path contains 'model' or 'entity'")
        if "repository" in name_lower or "dao" in name_lower or "repo" in name_lower:
            return RoleClassification(role="Repository", confidence="suspected", reason="filename or path contains 'repository' or 'dao'")
        if "util" in name_lower or "helper" in name_lower:
            return RoleClassification(role="Utility", confidence="suspected", reason="filename or path contains 'util' or 'helper'")
        if "component" in path_lower or name_lower.endswith(".tsx") or name_lower.endswith(".jsx"):
            return RoleClassification(role="Component", confidence="suspected", reason="filename or path indicates UI component")
        if "main" in name_lower or "index" in name_lower or "app" in name_lower:
            return RoleClassification(role="Entry Point", confidence="suspected", reason="filename indicates entry point")
            
        return RoleClassification(role="Unknown", confidence="none", reason="no heuristic patterns matched")

class ArchitectureAnalyzer:
    def __init__(self, domain_model: GraphModel, nx_graph: nx.DiGraph):
        self.domain_model = domain_model
        self.nx_graph = nx_graph
        self.rule_engine = RuleEngine()
        
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
            roles[node_id] = RoleClassifier.classify(node)
            
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
