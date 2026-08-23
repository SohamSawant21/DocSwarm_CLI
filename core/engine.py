from typing import Protocol, List, Optional
from pydantic import BaseModel
from core.models import FileNode, GraphModel, AnalysisResult

# Interfaces (Protocols) for the analysis pipeline stages
class Scanner(Protocol):
    def scan(self, target_path: str) -> List[FileNode]:
        """Scans the target path and returns a list of discovered files."""
        ...

class Analyzer(Protocol):
    def analyze(self, files: List[FileNode]) -> GraphModel:
        """Analyzes the files and constructs a dependency graph."""
        ...

class Reporter(Protocol):
    def generate_report(self, graph: GraphModel) -> str:
        """Generates a final report from the analyzed graph."""
        ...

# Dummy Implementations for Phase 1
class DummyScanner:
    def scan(self, target_path: str) -> List[FileNode]:
        # Return a dummy file node
        return [FileNode(id="dummy/path.py", path=f"{target_path}/dummy/path.py", name="path.py", role="Entry Points")]

class DummyAnalyzer:
    def analyze(self, files: List[FileNode]) -> GraphModel:
        graph = GraphModel()
        for f in files:
            graph.add_node(f)
        return graph

class DummyReporter:
    def generate_report(self, graph: GraphModel) -> str:
        return f"Dummy Report: {len(graph.nodes)} nodes analyzed."

class AnalysisService:
    """
    Orchestrates the codebase analysis lifecycle:
    Scanner -> Analyzer -> Reporter
    """
    def __init__(self, 
                 scanner: Optional[Scanner] = None, 
                 analyzer: Optional[Analyzer] = None, 
                 reporter: Optional[Reporter] = None):
        self.scanner = scanner or DummyScanner()
        self.analyzer = analyzer or DummyAnalyzer()
        self.reporter = reporter or DummyReporter()
        
    def analyze(self, target_path: str) -> AnalysisResult:
        """
        Executes the analysis pipeline synchronously and locally.
        """
        # 1. Scan
        files = self.scanner.scan(target_path)
        
        # 2. Analyze
        graph = self.analyzer.analyze(files)
        
        # 3. Report
        report = self.reporter.generate_report(graph)
        
        return AnalysisResult(graph=graph, report=report)
