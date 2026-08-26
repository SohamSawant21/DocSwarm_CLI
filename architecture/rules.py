from typing import List, Dict, Any
from pydantic import BaseModel
import networkx as nx

class RuleViolation(BaseModel):
    rule_id: str
    severity: str
    message: str
    penalty: int
    affected_files: List[str]
    status: str
    reason: str

from core.config import RuleConfig

class RuleEngine:
    def __init__(self, rules: List[RuleConfig]):
        self.rules = rules

    def evaluate(self, nx_graph: nx.DiGraph, cycles: List[List[str]], roles: Dict[str, Any]) -> List[RuleViolation]:
        violations = []
        
        # Rule A: Circular Dependency (Structural, non-configurable)
        if len(cycles) > 0:
            # Penalize once per existence of cycles (-15)
            affected = set()
            for cycle in cycles:
                affected.update(cycle)
            
            violations.append(RuleViolation(
                rule_id="ARCH-001",
                severity="high",
                message=f"Circular dependency detected involving {len(cycles)} cycle(s).",
                penalty=15,
                affected_files=sorted(list(affected)),
                status="confirmed",
                reason="Graph contains one or more cycles."
            ))
            
        # Rule B: Configurable Layer Violations
        for u, v in nx_graph.edges():
            role_u = roles.get(u)
            role_v = roles.get(v)
            
            if role_u and role_v:
                for rule in self.rules:
                    if role_u.role == rule.source_role and role_v.role == rule.forbidden_target_role:
                        violations.append(RuleViolation(
                            rule_id=rule.id,
                            severity=rule.severity,
                            message=f"{rule.source_role} {u} depends on {rule.forbidden_target_role} {v}.",
                            penalty=rule.penalty,  # Penalized per violation instance
                            affected_files=[u, v],
                            status="suspected",
                            reason=rule.message
                        ))

        return violations
