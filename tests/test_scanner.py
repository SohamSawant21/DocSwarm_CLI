import pytest
import os
from pathlib import Path
from scanner.scanner import WorkspaceScanner
from core.models import FileNode

def test_missing_target_path():
    """i. Missing target path raises an appropriate exception."""
    scanner = WorkspaceScanner()
    with pytest.raises(FileNotFoundError):
        scanner.scan("/this/path/absolutely/does/not/exist/12345")

def test_target_path_is_file(tmp_path):
    """j. Target path being a file raises an appropriate exception."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    scanner = WorkspaceScanner()
    with pytest.raises(NotADirectoryError):
        scanner.scan(str(test_file))

def test_basic_recursive_discovery(tmp_path):
    """a. Basic recursive discovery. b. Nested directories. k. Scanner output contains FileNode objects. h. IDs use forward slashes."""
    # Create structure:
    # root/
    #   main.py
    #   src/
    #     utils.py
    
    (tmp_path / "main.py").write_text("print('hello')")
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "utils.py").write_text("def test(): pass")
    
    scanner = WorkspaceScanner()
    nodes = scanner.scan(str(tmp_path))
    
    assert len(nodes) == 2
    for node in nodes:
        assert isinstance(node, FileNode)
        
    ids = {node.id for node in nodes}
    assert "main.py" in ids
    assert "src/utils.py" in ids # Checks forward slashes requirement

def test_ignored_directories(tmp_path):
    """c. Ignored directories such as .git and node_modules. d. .venv and __pycache__ are ignored."""
    (tmp_path / "app.py").write_text("import sys")
    
    # Create ignored dirs
    for ignored_name in [".git", "node_modules", ".venv", "__pycache__"]:
        ignored_dir = tmp_path / ignored_name
        ignored_dir.mkdir()
        (ignored_dir / "hidden.py").write_text("should be ignored")
        
    scanner = WorkspaceScanner()
    nodes = scanner.scan(str(tmp_path))
    
    assert len(nodes) == 1
    assert nodes[0].id == "app.py"

def test_binary_files_skipped(tmp_path):
    """e. Binary files are skipped."""
    (tmp_path / "script.py").write_text("print('text')")
    binary_file = tmp_path / "image.png"
    binary_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    
    scanner = WorkspaceScanner()
    nodes = scanner.scan(str(tmp_path))
    
    assert len(nodes) == 1
    assert nodes[0].id == "script.py"

def test_symlinks_skipped(tmp_path):
    """f. Symbolic links are not followed/skipped where supported."""
    (tmp_path / "real_file.py").write_text("real")
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    (real_dir / "inner.py").write_text("inner")
    
    # Try creating symlinks. On some Windows environments, this might require admin privileges.
    # We will try/except to gracefully skip if the OS prevents it during the test.
    try:
        os.symlink(str(real_dir), str(tmp_path / "linked_dir"))
        os.symlink(str(tmp_path / "real_file.py"), str(tmp_path / "linked_file.py"))
    except OSError:
        pytest.skip("Symlink creation not privileged on this OS for testing.")
        
    scanner = WorkspaceScanner()
    nodes = scanner.scan(str(tmp_path))
    
    # Should only find real_file.py and real_dir/inner.py
    ids = {node.id for node in nodes}
    assert len(ids) == 2
    assert "real_file.py" in ids
    assert "real_dir/inner.py" in ids
    assert "linked_file.py" not in ids
    assert "linked_dir/inner.py" not in ids

def test_language_detection(tmp_path):
    """g. Language detection for representative extensions."""
    files = {
        "test.py": "Python",
        "app.js": "JavaScript",
        "app.ts": "TypeScript",
        "app.jsx": "JSX",
        "app.tsx": "TSX",
        "data.json": "JSON",
        "config.yaml": "YAML",
        "README.md": "Markdown",
        "style.css": "CSS",
        "index.html": "HTML",
        "unknown.xyz": None
    }
    
    for filename in files.keys():
        (tmp_path / filename).write_text("dummy content")
        
    scanner = WorkspaceScanner()
    nodes = scanner.scan(str(tmp_path))
    
    assert len(nodes) == len(files)
    
    for node in nodes:
        expected_lang = files[node.id]
        assert node.language == expected_lang

def test_max_file_size_limits(tmp_path):
    """Verify that file size limits correctly bound scanning."""
    # 1. Normal file below limit
    normal_file = tmp_path / "normal.py"
    normal_file.write_bytes(b"a" * 1024) # 1 KB
    
    # 2. File exactly at the limit (using 2KB limit for this test)
    limit_file = tmp_path / "limit.py"
    limit_file.write_bytes(b"b" * 2048) # 2 KB
    
    # 3. Oversized file (1 byte over)
    oversized_file = tmp_path / "oversized.py"
    oversized_file.write_bytes(b"c" * 2049) # 2 KB + 1 byte
    
    # Scan with custom 2KB limit
    scanner = WorkspaceScanner(max_file_size_kb=2)
    nodes = scanner.scan(str(tmp_path))
    
    ids = {node.id for node in nodes}
    
    # Normal and exactly-at-limit should be included
    assert "normal.py" in ids
    assert "limit.py" in ids
    
    # Oversized should be skipped and reported
    assert "oversized.py" not in ids
    assert "oversized.py" in scanner.skipped_oversized
    
    # 4. Existing behavior unchanged (default limit)
    default_scanner = WorkspaceScanner()
    default_nodes = default_scanner.scan(str(tmp_path))
    default_ids = {node.id for node in default_nodes}
    
    # Since default limit is 2048 KB (2MB), all 3 files should be included
    assert "normal.py" in default_ids
    assert "limit.py" in default_ids
    assert "oversized.py" in default_ids
    assert len(default_scanner.skipped_oversized) == 0
