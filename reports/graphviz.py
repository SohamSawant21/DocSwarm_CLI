import os
import subprocess
from pathlib import Path
import networkx as nx
import pydot
from core.models import GraphModel
from architecture.analyzer import ArchitectureAnalysis

class GraphvizReporter:
    @staticmethod
    def export_dot(domain_model: GraphModel, analysis: ArchitectureAnalysis, output_dir: str = ".docswarm"):
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        file_path = out_path / "graph.dot"
        if not file_path.resolve().is_relative_to(Path(output_dir).resolve()):
            raise ValueError("Output path escapes target directory")

        # Create a pydot graph explicitly
        pydot_graph = pydot.Dot(graph_type='digraph', rankdir="LR")
        
        # Sort nodes and edges for deterministic output
        sorted_nodes = sorted(domain_model.nodes.items(), key=lambda x: x[0])
        for node_id, node in sorted_nodes:
            # Safe attributes
            role = analysis.role_classifications.get(node_id).role if node_id in analysis.role_classifications else "Unknown"
            label = f"{node_id}\\n({role})"
            pydot_node = pydot.Node(node_id, label=label, shape="box")
            pydot_graph.add_node(pydot_node)
            
        edges = domain_model.get_edges()
        internal_edges = [e for e in edges if e["type"] == "import" and e["target"] in domain_model.nodes]
        sorted_edges = sorted(internal_edges, key=lambda x: (x["source"], x["target"]))
        for edge in sorted_edges:
            pydot_edge = pydot.Edge(edge["source"], edge["target"])
            pydot_graph.add_edge(pydot_edge)
            
        file_path.write_text(pydot_graph.to_string(), encoding="utf-8")
        return str(file_path)

    @staticmethod
    def render_svg(dot_path: str, output_dir: str = ".docswarm"):
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        svg_path = out_path / "graph.svg"
        if not svg_path.resolve().is_relative_to(Path(output_dir).resolve()):
            raise ValueError("Output path escapes target directory")
            
        try:
            # We assume dot is on PATH
            result = subprocess.run(
                ["dot", "-Tsvg", dot_path, "-o", str(svg_path)],
                capture_output=True,
                text=True,
                check=True
            )
            return str(svg_path)
        except FileNotFoundError:
            raise RuntimeError("Graphviz 'dot' executable not found on PATH. Please ensure Graphviz is installed.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Graphviz rendering failed:\n{e.stderr}")
