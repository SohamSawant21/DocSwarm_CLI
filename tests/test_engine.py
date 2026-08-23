import pytest
import sys
import io
from unittest.mock import Mock, call
from core.engine import AnalysisService
from core.models import FileNode, GraphModel, AnalysisResult

def test_engine_instantiation():
    """Verify AnalysisService can be instantiated with default dummy implementations."""
    engine = AnalysisService()
    assert engine.scanner is not None
    assert engine.analyzer is not None
    assert engine.reporter is not None

def test_engine_analyze_execution():
    """Verify analyze executes successfully with dummy implementations."""
    engine = AnalysisService()
    result = engine.analyze("./sample")
    
    assert isinstance(result, AnalysisResult)
    assert isinstance(result.graph, GraphModel)
    assert isinstance(result.report, str)
    assert len(result.graph.nodes) > 0
    assert "Dummy Report" in result.report

def test_engine_execution_order_and_data_flow():
    """
    Verify the execution sequence: Scanner -> Analyzer -> Reporter,
    and verify that data flows correctly between stages.
    """
    mock_scanner = Mock()
    mock_analyzer = Mock()
    mock_reporter = Mock()
    
    # Setup mock returns
    dummy_files = [FileNode(id="test.py", path="/test.py", name="test.py")]
    dummy_graph = GraphModel()
    dummy_report = "Mock Report"
    
    mock_scanner.scan.return_value = dummy_files
    mock_analyzer.analyze.return_value = dummy_graph
    mock_reporter.generate_report.return_value = dummy_report
    
    engine = AnalysisService(
        scanner=mock_scanner,
        analyzer=mock_analyzer,
        reporter=mock_reporter
    )
    
    # Use a mock manager to track call order across different mocks
    from unittest.mock import MagicMock
    manager = MagicMock()
    manager.attach_mock(mock_scanner, 'scanner')
    manager.attach_mock(mock_analyzer, 'analyzer')
    manager.attach_mock(mock_reporter, 'reporter')
    
    result = engine.analyze("./mock_sample")
    
    # Verify execution order and data flow
    expected_calls = [
        call.scanner.scan("./mock_sample"),
        call.analyzer.analyze(dummy_files),
        call.reporter.generate_report(dummy_graph)
    ]
    assert manager.mock_calls == expected_calls
    
    # Verify final result
    assert result.graph == dummy_graph
    assert result.report == dummy_report

def test_engine_no_stdout_printing(capsys):
    """Verify the engine does not print to stdout during normal operation."""
    engine = AnalysisService()
    engine.analyze("./sample")
    
    captured = capsys.readouterr()
    assert captured.out == "", "Engine should not print to stdout"
    assert captured.err == "", "Engine should not print to stderr"
