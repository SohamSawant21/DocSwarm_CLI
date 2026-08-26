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

def test_downstream_missing_artifact(tmp_path):
    result = runner.invoke(app, ["deps", "a.py", str(tmp_path)])
    assert result.exit_code == 1
    assert "Analysis artifacts not found. Run 'docswarm analyze' first." in result.stdout

def test_downstream_invalid_json(tmp_path):
    art_dir = tmp_path / ".docswarm"
    art_dir.mkdir()
    (art_dir / "graph.json").write_text("{bad json")

    result = runner.invoke(app, ["deps", "a.py", str(tmp_path)])
    assert result.exit_code == 1
    assert "graph.json is corrupted or malformed." in result.stdout

def test_schema_version_mismatch(tmp_path):
    art_dir = tmp_path / ".docswarm"
    art_dir.mkdir()
    (art_dir / "graph.json").write_text(json.dumps({"graph": {}})) # missing version -> 1.0 assumed

    result = runner.invoke(app, ["deps", "a.py", str(tmp_path)])
    assert result.exit_code == 1
    assert "Artifact schema version 1.0 is not supported" in result.stdout

    (art_dir / "graph.json").write_text(json.dumps({"artifact_schema_version": "9.9"}))
    result2 = runner.invoke(app, ["deps", "a.py", str(tmp_path)])
    assert result2.exit_code == 1
    assert "Unsupported artifact schema version" in result2.stdout

def test_deps_missing_json(tmp_path):
    result = runner.invoke(app, ["deps", "a.py", str(tmp_path)])
    assert result.exit_code == 1
    assert "Analysis artifacts not found" in result.stdout

def test_analyze_workspace_without_config(tmp_path):
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 0

def test_analyze_workspace_with_valid_config(tmp_path):
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / ".docswarm.yaml").write_text("scanner:\n  max_file_size_kb: 4096\n", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 0

def test_analyze_workspace_with_invalid_config(tmp_path):
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / ".docswarm.yaml").write_text("scanner:\n  max_file_size_kb: 'huge'\n", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 1
    assert "Configuration Error" in result.stdout
    assert "Input should be a valid integer" in result.stdout
    # Ensure no python traceback is emitted
    assert "Traceback" not in result.stdout

def test_query_no_filters(tmp_path):
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])
    result = runner.invoke(app, ["query", str(tmp_path)])
    assert result.exit_code == 2
    assert "At least one filter must be provided" in result.output

def test_query_negative_validation(tmp_path):
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])
    result = runner.invoke(app, ["query", str(tmp_path), "--min-fan-in", "-1"])
    assert result.exit_code == 2
    assert "--min-fan-in must be >= 0" in result.output

def test_query_role_case_insensitive(tmp_path):
    (tmp_path / "my_model.py").write_text("import my_controller", encoding="utf-8")
    (tmp_path / "my_controller.py").write_text("def run(): pass", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])

    res1 = runner.invoke(app, ["query", str(tmp_path), "--role", "Model"])
    res2 = runner.invoke(app, ["query", str(tmp_path), "--role", "model"])
    res3 = runner.invoke(app, ["query", str(tmp_path), "--role", "MODEL"])

    assert res1.exit_code == 0
    assert "my_model.py" in res1.stdout
    assert "my_controller.py" not in res1.stdout
    assert res1.stdout == res2.stdout == res3.stdout

def test_query_intersection_and_sorting(tmp_path):
    (tmp_path / "a.py").write_text("import b\nimport c", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a", encoding="utf-8")
    (tmp_path / "c.py").write_text("def c(): pass", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])

    # b.py has fan-in = 1, fan-out = 1. a.py has fan-in=1, fan-out=2. c.py has fan-in=1, fan-out=0.
    # cycle between a.py and b.py

    # Query: has-cycles AND min-fan-out 2 -> Should only return a.py
    res = runner.invoke(app, ["query", str(tmp_path), "--has-cycles", "--min-fan-out", "2"])
    assert res.exit_code == 0
    assert "a.py\n" in res.stdout
    assert "b.py" not in res.stdout
    assert "c.py" not in res.stdout

def test_query_has_violations(tmp_path):
    # Trigger default ARCH-002: Model -> Controller
    (tmp_path / "my_model.py").write_text("import my_controller", encoding="utf-8")
    (tmp_path / "my_controller.py").write_text("pass", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])

    res = runner.invoke(app, ["query", str(tmp_path), "--has-violations"])
    assert res.exit_code == 0
    # my_model.py violates ARCH-002 by importing my_controller.py
    # This affects both the source and the target!
    assert "my_model.py" in res.stdout
    assert "my_controller.py" in res.stdout

def test_query_empty_result(tmp_path):
    (tmp_path / "a.py").write_text("pass", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])
    res = runner.invoke(app, ["query", str(tmp_path), "--has-cycles"])
    assert res.exit_code == 0
    assert res.stdout.strip() == ""

def test_query_bounded_warning(tmp_path):
    (tmp_path / "a.py").write_text("pass", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])

    # Mutate the artifact directly to simulate a bounded state
    import json
    json_path = tmp_path / ".docswarm" / "graph.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data["analysis"]["analysis_state"] = "bounded"
    json_path.write_text(json.dumps(data), encoding="utf-8")

    res = runner.invoke(app, ["query", str(tmp_path), "--has-cycles"])
    assert res.exit_code == 0
    assert "Warning: Artifact was bounded" in res.output
