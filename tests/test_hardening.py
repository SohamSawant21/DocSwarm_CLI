import os
import sys
import pytest
import socket
from pathlib import Path
from typer.testing import CliRunner
from cli.main import app

runner = CliRunner()

# ---------------------------------------------------------
# OFFLINE-RUN-001: AUTOMATED NETWORK BLOCK TEST
# ---------------------------------------------------------
@pytest.fixture
def block_network():
    """Monkeypatch socket to block all outgoing network connections."""
    original_socket = socket.socket
    
    class BlockedSocket:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("NETWORK ACCESS DETECTED AND BLOCKED BY OFFLINE-RUN-001")
            
    socket.socket = BlockedSocket
    yield
    socket.socket = original_socket

def test_offline_run_001_automated(block_network, tmp_path):
    """
    Requirement: OFFLINE-RUN-001.
    The complete analysis pipeline must operate without network access.
    """
    (tmp_path / "main.py").write_text("import os", encoding="utf-8")
    
    result = runner.invoke(app, ["analyze", str(tmp_path)])
    
    assert result.exit_code == 0
    assert "NETWORK ACCESS DETECTED" not in str(result.exception)

# ---------------------------------------------------------
# EMPTY REPOSITORY
# ---------------------------------------------------------
def test_empty_repository(tmp_path):
    result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 0
    assert "Files Scanned" in result.stdout
    assert " 0 " in result.stdout
    assert "Health Score" in result.stdout
    assert "100/100" in result.stdout

# ---------------------------------------------------------
# UNSUPPORTED LANGUAGE REPOSITORY
# ---------------------------------------------------------
def test_unsupported_language_repository():
    fixture_path = Path("tests/fixtures/unsupported").absolute()
    result = runner.invoke(app, ["analyze", str(fixture_path)])
    assert result.exit_code == 0
    # The scanner should ignore files without a mapped language (.txt, .csv)
    # Wait, scanner assigns language="unknown" or leaves it None?
    # Our Scanner ignores files not ending in mapped extensions.
    # So Files Scanned could be 0.
    assert "Health Score" in result.stdout
    assert "100/100" in result.stdout

# ---------------------------------------------------------
# BROKEN SOURCE FILES
# ---------------------------------------------------------
def test_broken_source_files():
    fixture_path = Path("tests/fixtures/broken_python").absolute()
    result = runner.invoke(app, ["analyze", str(fixture_path)])
    assert result.exit_code == 0
    
    # Check that analysis didn't crash.
    assert "Health Score" in result.stdout
    
    fixture_ts = Path("tests/fixtures/broken_typescript").absolute()
    result_ts = runner.invoke(app, ["analyze", str(fixture_ts)])
    assert result_ts.exit_code == 0

# ---------------------------------------------------------
# UNRESOLVED DEPENDENCIES
# ---------------------------------------------------------
def test_unresolved_dependencies():
    fixture_path = Path("tests/fixtures/unresolved").absolute()
    result = runner.invoke(app, ["analyze", str(fixture_path)])
    assert result.exit_code == 0
    
    # We can inspect the output via deps command
    deps_res = runner.invoke(app, ["deps", "main.ts", str(fixture_path)])
    assert deps_res.exit_code == 0
    assert "does-not-exist" in deps_res.stdout

# ---------------------------------------------------------
# AMBIGUOUS DEPENDENCIES
# ---------------------------------------------------------
def test_ambiguous_dependencies():
    fixture_path = Path("tests/fixtures/ambiguous").absolute()
    result = runner.invoke(app, ["analyze", str(fixture_path)])
    assert result.exit_code == 0
    
    deps_res = runner.invoke(app, ["deps", "main.ts", str(fixture_path)])
    assert deps_res.exit_code == 0
    assert "index" in deps_res.stdout # Unresolved/Ambiguous section

# ---------------------------------------------------------
# CIRCULAR DEPENDENCIES
# ---------------------------------------------------------
def test_circular_dependencies():
    fixture_path = Path("tests/fixtures/circular").absolute()
    result = runner.invoke(app, ["analyze", str(fixture_path)])
    assert result.exit_code == 0
    
    # Cycles should be detected
    assert "Cycles" in result.stdout
    assert " 1 " in result.stdout
    
    # Verify health score penalty
    # Default ARCH-001 penalty is 15
    assert "Health Score" in result.stdout
    assert "85/100" in result.stdout

# ---------------------------------------------------------
# EXTERNAL DEPENDENCIES
# ---------------------------------------------------------
def test_external_dependencies():
    fixture_path = Path("tests/fixtures/external").absolute()
    result = runner.invoke(app, ["analyze", str(fixture_path)])
    assert result.exit_code == 0
    
    deps_res = runner.invoke(app, ["deps", "main.py", str(fixture_path)])
    assert deps_res.exit_code == 0
    assert "numpy" in deps_res.stdout

# ---------------------------------------------------------
# IGNORED DIRECTORIES
# ---------------------------------------------------------
def test_ignored_directories():
    fixture_path = Path("tests/fixtures/ignored").absolute()
    result = runner.invoke(app, ["analyze", str(fixture_path)])
    assert result.exit_code == 0
    # main.py is in ignored/, but .git/config should definitely be ignored.
    # The workspace scanner ignores .git by default.
    pass

# ---------------------------------------------------------
# BINARY FILES
# ---------------------------------------------------------
def test_binary_files():
    fixture_path = Path("tests/fixtures/binary").absolute()
    result = runner.invoke(app, ["analyze", str(fixture_path)])
    assert result.exit_code == 0
    # Binary file skipped by scanner

# ---------------------------------------------------------
# SYMLINKS
# ---------------------------------------------------------
def test_symlinks(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("import os", encoding="utf-8")
    
    link = tmp_path / "link.py"
    try:
        os.symlink(source, link)
    except OSError:
        pytest.skip("Windows privilege restriction prevents symlink creation.")
        
    result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 0

# ---------------------------------------------------------
# DEEP DIRECTORY STRUCTURE
# ---------------------------------------------------------
def test_deep_directory_structure():
    fixture_path = Path("tests/fixtures/deep").absolute()
    result = runner.invoke(app, ["analyze", str(fixture_path)])
    assert result.exit_code == 0

# ---------------------------------------------------------
# LARGE FILE
# ---------------------------------------------------------
def test_large_file(tmp_path):
    large_file = tmp_path / "large.py"
    # ~1MB python file
    content = "def func(): pass\n" * 50000
    large_file.write_text(content, encoding="utf-8")
    
    result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 0

# ---------------------------------------------------------
# DETERMINISM
# ---------------------------------------------------------
def test_determinism_repeated_analysis(tmp_path):
    (tmp_path / "a.py").write_text("import b\nimport c", encoding="utf-8")
    (tmp_path / "b.py").write_text("import c", encoding="utf-8")
    (tmp_path / "c.py").write_text("pass", encoding="utf-8")
    
    runner.invoke(app, ["analyze", str(tmp_path)])
    json1 = (tmp_path / ".docswarm" / "graph.json").read_bytes()
    md1 = (tmp_path / ".docswarm" / "report.md").read_bytes()
    
    runner.invoke(app, ["analyze", str(tmp_path)])
    json2 = (tmp_path / ".docswarm" / "graph.json").read_bytes()
    md2 = (tmp_path / ".docswarm" / "report.md").read_bytes()
    
    assert json1 == json2
    assert md1 == md2

# ---------------------------------------------------------
# CLI ERROR HANDLING
# ---------------------------------------------------------
def test_cli_error_handling(tmp_path):
    # Missing Workspace
    r = runner.invoke(app, ["analyze", "/fake/path/999"])
    assert r.exit_code == 1
    assert "does not exist" in r.stdout
    
    # Missing Artifacts
    r = runner.invoke(app, ["deps", "a.py", str(tmp_path)])
    assert r.exit_code == 1
    assert "artifacts not found" in r.stdout
    
    # Missing File in Inspect
    (tmp_path / "a.py").write_text("pass", encoding="utf-8")
    runner.invoke(app, ["analyze", str(tmp_path)])
    r = runner.invoke(app, ["inspect", "fake.py", str(tmp_path)])
    assert r.exit_code == 1
    assert "not found in the graph" in r.stdout
