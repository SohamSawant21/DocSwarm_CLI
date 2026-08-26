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

from core.engine import AnalysisService

def get_workspace_dir(path: str) -> Path:
    target = Path(path).resolve()
    if not target.exists():
        console.print(f"[red]Error: Target path '{target}' does not exist.[/red]")
        raise typer.Exit(code=1)
    return target

def load_graph_json(target: Path) -> tuple[GraphModel, ArchitectureAnalysis]:
    json_path = target / ".docswarm" / "graph.json"
    if not json_path.exists():
        console.print("[red]Analysis artifacts not found. Run 'docswarm analyze' first.[/red]")
        raise typer.Exit(code=1)
        
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        console.print("[red]graph.json is corrupted or malformed.[/red]")
        raise typer.Exit(code=1)
        
    schema_version = data.get("artifact_schema_version")
    if not schema_version or schema_version == "1.0":
        console.print("[red]Artifact schema version 1.0 is not supported in v0.2.0. Please run 'docswarm analyze' to upgrade.[/red]")
        raise typer.Exit(code=1)
    elif schema_version != "1.1":
        console.print("[red]Unsupported artifact schema version. Please upgrade docswarm.[/red]")
        raise typer.Exit(code=1)

    try:
        domain_model = GraphModel.model_validate(data["graph"])
        analysis = ArchitectureAnalysis.model_validate(data["analysis"])
        return domain_model, analysis
    except KeyError as e:
        console.print(f"[red]Malformed artifact: missing required field {e}[/red]")
        raise typer.Exit(code=1)

@app.command("analyze")
def analyze(path: str = typer.Argument(".")):
    """
    Run the complete architecture analysis pipeline.
    """
    target = get_workspace_dir(path)
    
    from core.config import load_config, ConfigValidationError
    try:
        config = load_config(target)
    except ConfigValidationError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        raise typer.Exit(code=1)
        
    with console.status(f"[bold green]Analyzing workspace at {target}..."):
        try:
            service = AnalysisService(config=config)
            result = service.analyze(str(target))
            
            domain_model = result.graph
            analysis = result.analysis
            parsing_report = result.parsing_report
            file_nodes = list(domain_model.nodes.values())
            
            # 6. Reporting
            out_dir = str(target / ".docswarm")
            MarkdownReporter.render(domain_model, analysis, out_dir)
            JSONExporter.export(result, out_dir)
            
            from reports.html_reporter import HTMLReporter
            HTMLReporter.export(result, out_dir)
            
            dot_path = GraphvizReporter.export_dot(domain_model, analysis, out_dir)
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
    summary.add_row("Analysis State", f"[yellow]{result.analysis_state}[/yellow]" if result.analysis_state == "bounded" else f"[green]{result.analysis_state}[/green]")
    summary.add_row("Files Scanned", str(len(file_nodes)))
    summary.add_row("Graph Nodes", str(analysis.metrics.num_nodes))
    summary.add_row("Internal Edges", str(analysis.metrics.num_edges))
    summary.add_row("Cycles", str(analysis.metrics.num_cycles))
    summary.add_row("Hotspots", str(len(analysis.hotspots)))
    summary.add_row("Rule Violations", str(len(analysis.violations)))
    
    # Add parsing report details if any
    if parsing_report.parser_exceptions:
        summary.add_row("Parser Errors", str(len(parsing_report.parser_exceptions)))
    if parsing_report.syntax_errors:
        summary.add_row("Syntax Errors", str(len(parsing_report.syntax_errors)))
    if parsing_report.skipped_binary or parsing_report.skipped_oversized:
        skipped = len(parsing_report.skipped_binary) + len(parsing_report.skipped_oversized)
        summary.add_row("Skipped Files", str(skipped))
    
    console.print()
    console.print(Panel(summary, expand=False))
    
    if parsing_report.parser_exceptions:
        console.print("[yellow]Files with parser exceptions:[/yellow]")
        for f, err in parsing_report.parser_exceptions.items():
            console.print(f"  - {f}: {err}")
            
    if parsing_report.syntax_errors:
        console.print("[yellow]Files with syntax errors (parsed partially):[/yellow]")
        for f in parsing_report.syntax_errors[:5]:
            console.print(f"  - {f}")
        if len(parsing_report.syntax_errors) > 5:
            console.print(f"  ... and {len(parsing_report.syntax_errors) - 5} more.")
            
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
    domain_model, analysis = load_graph_json(target)
    
    out_dir = str(target / ".docswarm")
    try:
        dot_path = GraphvizReporter.export_dot(domain_model, analysis, out_dir)
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
