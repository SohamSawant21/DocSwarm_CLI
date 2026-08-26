from core.models import FileNode, GraphModel, AnalysisResult, ParsingReport
from core.config import DocSwarmConfig
from scanner.scanner import WorkspaceScanner
from parsers.registry import ParserRegistry
from parsers.python import PythonParser
from parsers.javascript import JavaScriptParser
from parsers.typescript import TypeScriptParser
from resolver.resolver import WorkspaceResolver
from graph.builder import GraphBuilder
from architecture.analyzer import ArchitectureAnalyzer, ArchitectureAnalysis
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AnalysisService:
    """
    Orchestrates the codebase analysis lifecycle:
    Scanner -> Parser -> Resolver -> Graph Builder -> Analyzer
    """
    def __init__(self, config: DocSwarmConfig | None = None):
        self.config = config or DocSwarmConfig()
        self.scanner = WorkspaceScanner(self.config.scanner)
        self.registry = ParserRegistry()
        
        # Explicit parser registration (Phase 1 requirement)
        self.registry.register("python", PythonParser())
        self.registry.register("javascript", JavaScriptParser())
        self.registry.register("typescript", TypeScriptParser())
        
    def analyze(self, target_path: str) -> AnalysisResult:
        """
        Executes the analysis pipeline synchronously and locally.
        """
        target = Path(target_path).resolve()
        
        # 1. Scan
        file_nodes = self.scanner.scan(str(target))
        
        parsing_report = ParsingReport(
            skipped_binary=self.scanner.skipped_binary,
            skipped_oversized=self.scanner.skipped_oversized,
        )
        
        # 2. Parse & 3. Resolve
        for node in file_nodes:
            if not node.language:
                continue
                
            try:
                parser = self.registry.get_parser(node.language)
            except (NotImplementedError, ValueError):
                continue
                
            abs_path = target / node.id
            try:
                content = abs_path.read_bytes()
                metadata = parser.parse(node, content)
                
                if metadata.has_syntax_error:
                    parsing_report.syntax_errors.append(node.id)
                    
                resolver = WorkspaceResolver(file_nodes, str(target))
                node.dependencies = resolver.resolve(node, metadata)
                
            except Exception as e:
                # Catch, log, and report parser_exception without halting
                logger.debug(f"Failed to parse {node.id}: {e}")
                parsing_report.parser_exceptions[node.id] = str(e)

        # 4. Build Graph
        builder = GraphBuilder()
        domain_model = builder.build(file_nodes)
        
        # 5. Architecture Analysis
        analyzer = ArchitectureAnalyzer(domain_model, builder.nx_graph)
        analysis = analyzer.analyze()
        
        return AnalysisResult(
            graph=domain_model,
            analysis=analysis,
            parsing_report=parsing_report
        )
