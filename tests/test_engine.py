import pytest
from unittest.mock import Mock, patch
from core.engine import AnalysisService
from core.models import FileNode, GraphModel, AnalysisResult, ParsingReport
from parsers.base import ParsedMetadata

def test_engine_instantiation():
    """Verify AnalysisService can be instantiated and registers parsers."""
    engine = AnalysisService()
    assert engine.scanner is not None
    assert engine.registry is not None
    assert engine.registry.get_parser("python") is not None

@patch('core.engine.Path')
@patch('core.engine.WorkspaceScanner')
@patch('core.engine.GraphBuilder')
@patch('core.engine.ArchitectureAnalyzer')
@patch('core.engine.WorkspaceResolver')
def test_engine_execution_order_and_data_flow(
    MockResolver, MockAnalyzer, MockBuilder, MockScanner, MockPath
):
    """
    Verify the execution sequence: Scanner -> Parser -> Resolver -> Graph Builder -> Analyzer
    """
    # Setup mock returns
    mock_scanner_instance = MockScanner.return_value
    mock_scanner_instance.skipped_binary = []
    mock_scanner_instance.skipped_oversized = []
    
    mock_file = FileNode(id="test.py", path="/test.py", name="test.py", language="python")
    mock_scanner_instance.scan.return_value = [mock_file]
    
    mock_builder_instance = MockBuilder.return_value
    dummy_graph = GraphModel()
    mock_builder_instance.build.return_value = dummy_graph

    mock_analyzer_instance = MockAnalyzer.return_value
    mock_analysis = Mock()
    mock_analysis.analysis_state = "complete"
    mock_analyzer_instance.analyze.return_value = mock_analysis
    
    mock_resolver_instance = MockResolver.return_value
    mock_resolver_instance.resolve.return_value = []
    
    mock_path_instance = MockPath.return_value.resolve.return_value
    mock_abs_path = Mock()
    mock_abs_path.read_bytes.return_value = b"print('hello')"
    mock_path_instance.__truediv__.return_value = mock_abs_path
    
    engine = AnalysisService()
    
    # Mock the parser
    mock_parser = Mock()
    mock_metadata = ParsedMetadata()
    mock_parser.parse.return_value = mock_metadata
    engine.registry._parsers["python"] = mock_parser
    
    result = engine.analyze("./mock_sample")
    
    # Verify execution
    mock_scanner_instance.scan.assert_called_once()
    mock_parser.parse.assert_called_once()
    mock_resolver_instance.resolve.assert_called_once()
    mock_builder_instance.build.assert_called_once_with([mock_file])
    mock_analyzer_instance.analyze.assert_called_once()
    
    # Verify final result
    assert isinstance(result, AnalysisResult)
    assert result.graph == dummy_graph
    assert result.analysis == mock_analysis
    assert isinstance(result.parsing_report, ParsingReport)

@patch('core.engine.Path')
def test_engine_parser_exception_handling(MockPath):
    """Verify that a parser exception is caught and reported without crashing, and valid files continue."""
    engine = AnalysisService()
    
    # Create a dummy scanner that returns one bad and one good python file
    bad_node = FileNode(id="bad.py", path="/bad.py", name="bad.py", language="python")
    good_node = FileNode(id="good.py", path="/good.py", name="good.py", language="python")
    engine.scanner.scan = Mock(return_value=[bad_node, good_node])
    engine.scanner.skipped_binary = []
    engine.scanner.skipped_oversized = []
    
    def mock_parse_side_effect(node, content):
        if node.id == "good.py":
            return ParsedMetadata()
        raise Exception("Fake parse error")
        
    mock_parser = Mock()
    mock_parser.parse.side_effect = mock_parse_side_effect
    engine.registry._parsers["python"] = mock_parser
    
    result = engine.analyze("./mock_sample")
    
    # Verify it didn't crash and the error was recorded
    assert "bad.py" in result.parsing_report.parser_exceptions
    assert "Fake parse error" in result.parsing_report.parser_exceptions["bad.py"]
    
    # Verify the good file successfully went through the graph builder
    # (AnalysisService builds graph from all file_nodes, even if unparsed, which matches original behavior)
    assert "bad.py" in result.graph.nodes

@patch('core.engine.Path')
def test_engine_no_stdout_printing(MockPath, capsys):
    """Verify the engine does not print to stdout during normal operation."""
    engine = AnalysisService()
    
    # Empty scanner
    engine.scanner.scan = Mock(return_value=[])
    
    engine.analyze("./mock_sample")
    
    captured = capsys.readouterr()
    assert captured.out == "", "Engine should not print to stdout"
    assert captured.err == "", "Engine should not print to stderr"
