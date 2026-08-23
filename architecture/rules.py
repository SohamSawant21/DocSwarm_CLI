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

class RuleEngine:
    def __init__(self):
        pass

    def evaluate(self, nx_graph: nx.DiGraph, cycles: List[List[str]], roles: Dict[str, Any]) -> List[RuleViolation]:
        violations = []
        
        # Rule A: Circular Dependency
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
            
        # Rule B: Suspected Layer Violation
        # E.g., Model -> Controller is a violation.
        for u, v in nx_graph.edges():
            role_u = roles.get(u)
            role_v = roles.get(v)
            
            if role_u and role_v:
                if role_u.role == "Model" and role_v.role == "Controller":
                    violations.append(RuleViolation(
                        rule_id="ARCH-002",
                        severity="medium",
                        message=f"Model {u} depends on Controller {v}.",
                        penalty=10,  # Penalized per violation instance
                        affected_files=[u, v],
                        status="suspected",
                        reason="Models typically should not depend on Controllers in layered architectures."
                    ))
                elif role_u.role == "Model" and role_v.role == "Service":
                    # Another common layered violation if strict layering is assumed
                    violations.append(RuleViolation(
                        rule_id="ARCH-003",
                        severity="low",
                        message=f"Model {u} depends on Service {v}.",
                        penalty=5,
                        affected_files=[u, v],
                        status="suspected",
                        reason="Models typically should not depend on Services."
                    ))

        return violations
