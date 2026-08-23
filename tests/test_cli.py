import pytest
from typer.testing import CliRunner
from cli.main import app
import json
from pathlib import Path

runner = CliRunner()

def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "DocSwarm" in result.stdout

def test_analyze_invalid_path():
    result = runner.invoke(app, ["analyze", "/does/not/exist/ever"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout

def test_analyze_success(tmp_path):
    # Create dummy workspace
    (tmp_path / "a.py").write_text("import b\nimport pandas", encoding="utf-8")
    (tmp_path / "b.py").write_text("def x(): pass", encoding="utf-8")
    
    result = runner.invoke(app, ["analyze", str(tmp_path)])
    
    assert result.exit_code == 0
    assert "Architecture Analysis Summary" in result.stdout
    assert "Health Score" in result.stdout
    
    # Check artifacts
    assert (tmp_path / ".docswarm" / "graph.json").exists()
    assert (tmp_path / ".docswarm" / "report.md").exists()
    assert (tmp_path / ".docswarm" / "graph.dot").exists()
    
def test_deps(tmp_path):
    # Needs valid artifacts
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / "b.py").write_text("pass", encoding="utf-8")
    r1 = runner.invoke(app, ["analyze", str(tmp_path)])
    print("Analyze output:", r1.stdout)
    
    result = runner.invoke(app, ["deps", "a.py", str(tmp_path)])
    print("Deps output:", result.stdout)
    assert result.exit_code == 0
    assert "Dependencies: a.py" in result.stdout
    assert "b.py" in result.stdout
    
def test_inspect(tmp_path):
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])
    
    result = runner.invoke(app, ["inspect", "a.py", str(tmp_path)])
    assert result.exit_code == 0
    assert "Inspection: a.py" in result.stdout
    assert "Fan-out" in result.stdout

def test_graph(tmp_path):
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])
    
    result = runner.invoke(app, ["graph", str(tmp_path)])
    assert result.exit_code == 0
    assert "DOT generated" in result.stdout
    
def test_report(tmp_path):
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])
    
    result = runner.invoke(app, ["report", str(tmp_path)])
    assert result.exit_code == 0
    assert "Report generated" in result.stdout

def test_deps_missing_json(tmp_path):
    result = runner.invoke(app, ["deps", "a.py", str(tmp_path)])
    assert result.exit_code == 1
    assert "Analysis artifacts not found" in result.stdout
