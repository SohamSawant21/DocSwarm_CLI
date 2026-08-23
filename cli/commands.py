import os
import json
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.models import GraphModel
from scanner.scanner import WorkspaceScanner
from parsers.registry import ParserRegistry
from resolver.resolver import WorkspaceResolver
from graph.builder import GraphBuilder
from architecture.analyzer import ArchitectureAnalyzer, ArchitectureAnalysis
from reports.markdown import MarkdownReporter
from reports.json_exporter import JSONExporter
from reports.graphviz import GraphvizReporter

app = typer.Typer(help="DocSwarm CLI for architecture analysis.")
console = Console()

def get_workspace_dir(path: str) -> Path:
    target = Path(path).resolve()
    if not target.exists():
        console.print(f"[red]Error: Target path '{target}' does not exist.[/red]")
        raise typer.Exit(code=1)
    return target

def load_graph_json(target: Path) -> tuple[GraphModel, ArchitectureAnalysis]:
    json_path = target / ".docswarm" / "graph.json"
    if not json_path.exists():
        console.print(f"[red]Error: Analysis artifacts not found at '{json_path}'. Run 'docswarm analyze' first.[/red]")
        raise typer.Exit(code=1)
        
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        domain_model = GraphModel.model_validate(data["graph"])
        analysis = ArchitectureAnalysis.model_validate(data["analysis"])
        return domain_model, analysis
    except Exception as e:
        console.print(f"[red]Error parsing graph.json: {e}[/red]")
        raise typer.Exit(code=1)

@app.command("analyze")
def analyze(path: str = typer.Argument(".")):
    """
    Run the complete architecture analysis pipeline.
    """
    target = get_workspace_dir(path)
    
    with console.status(f"[bold green]Analyzing workspace at {target}..."):
        try:
            # 1. Scan
            scanner = WorkspaceScanner()
            file_nodes = scanner.scan(str(target))
            
            # 2. Parse
            registry = ParserRegistry()
            # Register parsers manually if they weren't imported/registered
            from parsers.python import PythonParser
            from parsers.javascript import JavaScriptParser
            from parsers.typescript import TypeScriptParser
            registry.register("python", PythonParser())
            registry.register("javascript", JavaScriptParser())
            registry.register("typescript", TypeScriptParser())

            for node in file_nodes:
                if node.language:
                    try:
                        parser = registry.get_parser(node.language)
                        # Note: We need the full absolute path for Tree-sitter
                        abs_path = str(target / node.id)
                        try:
                            content = Path(abs_path).read_bytes()
                            metadata = parser.parse(node, content)
                            # 3. Resolve
                            resolver = WorkspaceResolver(file_nodes, str(target))
                            node.dependencies = resolver.resolve(node, metadata)
                        except Exception as e:
                            # Skip files that can't be read or parsed safely
                            pass
                    except (NotImplementedError, ValueError):
                        # Unsupported language
                        pass

            # 4. Build Graph
            builder = GraphBuilder()
            domain_model = builder.build(file_nodes)
            
            # 5. Architecture Analysis
            analyzer = ArchitectureAnalyzer(domain_model, builder.nx_graph)
            analysis = analyzer.analyze()
            
            # 6. Reporting
            out_dir = str(target / ".docswarm")
            MarkdownReporter.render(domain_model, analysis, out_dir)
            JSONExporter.export(domain_model, analysis, out_dir)
            dot_path = GraphvizReporter.export_dot(builder.nx_graph, out_dir)
            try:
                GraphvizReporter.render_svg(dot_path, out_dir)
                svg_status = "Generated"
            except RuntimeError as e:
                svg_status = "Failed (Graphviz not found)"

        except Exception as e:
            console.print(f"[red]Analysis failed: {e}[/red]")
            raise typer.Exit(code=1)

    # 7. Rich Summary
    summary = Table(title="Architecture Analysis Summary", show_header=False)
    summary.add_column("Metric", style="cyan")
    summary.add_column("Value", style="magenta")
    
    summary.add_row("Health Score", f"{analysis.health_score}/100")
    summary.add_row("Files Scanned", str(len(file_nodes)))
    summary.add_row("Graph Nodes", str(analysis.metrics.num_nodes))
    summary.add_row("Internal Edges", str(analysis.metrics.num_edges))
    summary.add_row("Cycles", str(analysis.metrics.num_cycles))
    summary.add_row("Hotspots", str(len(analysis.hotspots)))
    summary.add_row("Rule Violations", str(len(analysis.violations)))
    
    console.print()
    console.print(Panel(summary, expand=False))
    console.print(f"[green]Artifacts saved to:[/green] {out_dir}")
    if svg_status != "Generated":
        console.print(f"[yellow]SVG Status: {svg_status}[/yellow]")

@app.command("deps")
def deps(file: str = typer.Argument(...), path: str = typer.Argument(".")):
    """
    Display dependency relationships for a single file.
    """
    target = get_workspace_dir(path)
    domain_model, _ = load_graph_json(target)
    
    # Normalize path separators for lookups
    file_id = Path(file).as_posix()
    
    if file_id not in domain_model.nodes:
        console.print(f"[red]Error: File '{file_id}' not found in the graph.[/red]")
        raise typer.Exit(code=1)
        
    node = domain_model.nodes[file_id]
    
    # Calculate incoming by scanning others
    incoming = []
    for other_id, other_node in domain_model.nodes.items():
        for d in other_node.dependencies:
            if d.type == "import" and d.target_id == file_id:
                incoming.append(other_id)
                
    # Outgoing
    outgoing = [d.target_id for d in node.dependencies if d.type == "import"]
    external = [d.target_id for d in node.dependencies if d.type == "external"]
    unresolved = [d.target_id for d in node.dependencies if d.type in ("unresolved", "ambiguous")]
    
    t = Table(title=f"Dependencies: {file_id}")
    t.add_column("Category", style="cyan")
    t.add_column("Files", style="green")
    
    t.add_row("Incoming (Internal)", "\n".join(incoming) if incoming else "None")
    t.add_row("Outgoing (Internal)", "\n".join(outgoing) if outgoing else "None")
    t.add_row("External", "\n".join(external) if external else "None")
    t.add_row("Unresolved/Ambiguous", "\n".join(unresolved) if unresolved else "None")
    
    console.print(t)

@app.command("inspect")
def inspect(file: str = typer.Argument(...), path: str = typer.Argument(".")):
    """
    Display comprehensive architectural information for a file.
    """
    target = get_workspace_dir(path)
    domain_model, analysis = load_graph_json(target)
    
    # Normalize path separators for lookups
    file_id = Path(file).as_posix()
    
    if file_id not in domain_model.nodes:
        console.print(f"[red]Error: File '{file_id}' not found in the graph.[/red]")
        raise typer.Exit(code=1)
        
    node = domain_model.nodes[file_id]
    role = analysis.role_classifications.get(file_id)
    fin = analysis.metrics.fan_in.get(file_id, 0)
    fout = analysis.metrics.fan_out.get(file_id, 0)
    
    hotspots = [h for h in analysis.hotspots if h.node == file_id]
    cycles = [c for c in analysis.cycles if file_id in c]
    violations = [v for v in analysis.violations if file_id in v.affected_files]
    
    t = Table(title=f"Inspection: {file_id}", show_header=False)
    t.add_column("Property", style="cyan")
    t.add_column("Value")
    
    t.add_row("Path", node.path)
    if role:
        t.add_row("Role", f"{role.role} (confidence: {role.confidence})")
    t.add_row("Fan-in", str(fin))
    t.add_row("Fan-out", str(fout))
    t.add_row("Hotspot", "Yes" if hotspots else "No")
    t.add_row("Involved in Cycles", str(len(cycles)))
    t.add_row("Architecture Violations", str(len(violations)))
    
    console.print(t)

@app.command("graph")
def graph(path: str = typer.Argument(".")):
    """
    Generate graph artifacts explicitly.
    """
    target = get_workspace_dir(path)
    domain_model, _ = load_graph_json(target)
    
    import networkx as nx
    nx_graph = nx.DiGraph()
    for n_id, n in domain_model.nodes.items():
        nx_graph.add_node(n_id, label=n.name, language=n.language, role=n.role)
    for n_id, n in domain_model.nodes.items():
        for d in n.dependencies:
            if d.type == "import" and d.target_id in domain_model.nodes:
                nx_graph.add_edge(n_id, d.target_id)
                
    out_dir = str(target / ".docswarm")
    try:
        dot_path = GraphvizReporter.export_dot(nx_graph, out_dir)
        console.print(f"[green]DOT generated at:[/green] {dot_path}")
        try:
            svg_path = GraphvizReporter.render_svg(dot_path, out_dir)
            console.print(f"[green]SVG generated at:[/green] {svg_path}")
        except RuntimeError as e:
            console.print(f"[yellow]SVG failed: {e}[/yellow]")
            raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Graph generation failed: {e}[/red]")
        raise typer.Exit(code=1)

@app.command("report")
def report(path: str = typer.Argument(".")):
    """
    Regenerate Markdown report from existing graph data.
    """
    target = get_workspace_dir(path)
    domain_model, analysis = load_graph_json(target)
    
    try:
        out_dir = str(target / ".docswarm")
        report_path = MarkdownReporter.render(domain_model, analysis, out_dir)
        console.print(f"[green]Report generated at:[/green] {report_path}")
    except Exception as e:
        console.print(f"[red]Report generation failed: {e}[/red]")
        raise typer.Exit(code=1)
