import os
from pathlib import Path
from core.models import GraphModel
from architecture.analyzer import ArchitectureAnalysis

class MarkdownReporter:
    @staticmethod
    def render(domain_model: GraphModel, analysis: ArchitectureAnalysis, output_dir: str = ".docswarm"):
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        file_path = out_path / "report.md"
        # Ensure path safety
        if not file_path.resolve().is_relative_to(Path(output_dir).resolve()):
            raise ValueError("Output path escapes target directory")

        lines = [
            "# Architecture Analysis Report",
            "",
            "## Summary",
            f"- **Health Score**: {analysis.health_score}/100",
            f"- **Total Nodes**: {analysis.metrics.num_nodes}",
            f"- **Total Internal Edges**: {analysis.metrics.num_edges}",
            f"- **Total Cycles**: {analysis.metrics.num_cycles}",
            ""
        ]
        
        # Rule Violations
        lines.extend(["## Violations", ""])
        if not analysis.violations:
            lines.append("No architecture violations detected.\n")
        else:
            # Sort for determinism
            sorted_violations = sorted(analysis.violations, key=lambda v: (v.rule_id, v.message))
            for v in sorted_violations:
                lines.extend([
                    f"### [{v.rule_id}] {v.severity.upper()} - {v.status.upper()}",
                    f"**Message**: {v.message}",
                    f"**Penalty**: -{v.penalty}",
                    f"**Reason**: {v.reason}",
                    f"**Affected Files**: {', '.join(sorted(v.affected_files))}",
                    ""
                ])

        # Cycles
        lines.extend(["## Cycles", ""])
        if not analysis.cycles:
            lines.append("No circular dependencies detected.\n")
        else:
            sorted_cycles = sorted([sorted(c) for c in analysis.cycles])
            for i, cycle in enumerate(sorted_cycles):
                lines.append(f"{i+1}. `{'` -> `'.join(cycle)}`")
            lines.append("")
            
        # Hotspots
        lines.extend(["## Hotspots", ""])
        if not analysis.hotspots:
            lines.append("No hotspots detected.\n")
        else:
            sorted_hotspots = sorted(analysis.hotspots, key=lambda h: (h.node, h.metric))
            for h in sorted_hotspots:
                lines.extend([
                    f"- **{h.node}**",
                    f"  - Metric: {h.metric} ({h.value})",
                    f"  - Reason: {h.reason}"
                ])
            lines.append("")
            
        # Role Classifications
        lines.extend(["## Role Classifications", ""])
        sorted_roles = sorted(analysis.role_classifications.items(), key=lambda x: x[0])
        for node_id, role_info in sorted_roles:
            lines.append(f"- **{node_id}**: {role_info.role} (confidence: {role_info.confidence})")
            
        lines.append("")

        file_path.write_text("\n".join(lines), encoding="utf-8")
        return str(file_path)
