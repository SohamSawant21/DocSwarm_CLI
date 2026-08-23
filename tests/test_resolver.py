import pytest
import os
from pathlib import Path
from core.models import FileNode, Dependency
from parsers.base import ParsedMetadata, ImportData
from resolver.resolver import WorkspaceResolver
from graph.builder import GraphBuilder

def test_relative_typescript_import(tmp_path):
    """A. Relative TypeScript import & C. Extension resolution"""
    f1 = FileNode(id="src/a.ts", path=str(tmp_path / "src/a.ts"), name="a.ts")
    f2 = FileNode(id="src/b.ts", path=str(tmp_path / "src/b.ts"), name="b.ts")
    
    resolver = WorkspaceResolver([f1, f2], str(tmp_path))
    meta = ParsedMetadata(imports=[ImportData(module="./b")])
    deps = resolver.resolve(f1, meta)
    
    assert len(deps) == 1
    assert deps[0].target_id == "src/b.ts"
    assert deps[0].type == "import"

def test_nested_relative_import(tmp_path):
    """B. Nested relative import"""
    f1 = FileNode(id="src/services/a.ts", path=str(tmp_path / "src/services/a.ts"), name="a.ts")
    f2 = FileNode(id="src/utils/b.ts", path=str(tmp_path / "src/utils/b.ts"), name="b.ts")
    
    resolver = WorkspaceResolver([f1, f2], str(tmp_path))
    meta = ParsedMetadata(imports=[ImportData(module="../utils/b")])
    deps = resolver.resolve(f1, meta)
    
    assert len(deps) == 1
    assert deps[0].target_id == "src/utils/b.ts"

def test_index_resolution(tmp_path):
    """D. Index resolution"""
    f1 = FileNode(id="src/a.ts", path=str(tmp_path / "src/a.ts"), name="a.ts")
    f2 = FileNode(id="src/utils/index.ts", path=str(tmp_path / "src/utils/index.ts"), name="index.ts")
    
    resolver = WorkspaceResolver([f1, f2], str(tmp_path))
    meta = ParsedMetadata(imports=[ImportData(module="./utils")])
    deps = resolver.resolve(f1, meta)
    
    assert len(deps) == 1
    assert deps[0].target_id == "src/utils/index.ts"

def test_typescript_alias(tmp_path):
    """E. TypeScript alias using tsconfig.json"""
    tsconfig = tmp_path / "tsconfig.json"
    tsconfig.write_text('{"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"]}}}')
    
    f1 = FileNode(id="main.ts", path=str(tmp_path / "main.ts"), name="main.ts")
    f2 = FileNode(id="src/components/Button.tsx", path=str(tmp_path / "src/components/Button.tsx"), name="Button.tsx")
    
    resolver = WorkspaceResolver([f1, f2], str(tmp_path))
    meta = ParsedMetadata(imports=[ImportData(module="@/components/Button")])
    deps = resolver.resolve(f1, meta)
    
    assert len(deps) == 1
    assert deps[0].target_id == "src/components/Button.tsx"

def test_malformed_tsconfig(tmp_path):
    """Test malformed tsconfig falls back safely."""
    tsconfig = tmp_path / "tsconfig.json"
    tsconfig.write_text('{ malformed json ! }')
    
    f1 = FileNode(id="main.ts", path=str(tmp_path / "main.ts"), name="main.ts")
    
    # Should not crash
    resolver = WorkspaceResolver([f1], str(tmp_path))
    assert resolver.tsconfig == {}

def test_external_package(tmp_path):
    """F. External package does not create internal edge"""
    f1 = FileNode(id="src/a.ts", path=str(tmp_path / "src/a.ts"), name="a.ts")
    
    resolver = WorkspaceResolver([f1], str(tmp_path))
    meta = ParsedMetadata(imports=[ImportData(module="react")])
    deps = resolver.resolve(f1, meta)
    
    assert len(deps) == 1
    assert deps[0].target_id == "react"
    assert deps[0].type == "external"

def test_unresolved_import(tmp_path):
    """G. Unresolved import"""
    f1 = FileNode(id="src/a.ts", path=str(tmp_path / "src/a.ts"), name="a.ts")
    
    resolver = WorkspaceResolver([f1], str(tmp_path))
    meta = ParsedMetadata(imports=[ImportData(module="./does-not-exist")])
    deps = resolver.resolve(f1, meta)
    
    assert len(deps) == 1
    assert deps[0].target_id == "./does-not-exist"
    assert deps[0].type == "unresolved"

def test_ambiguous_import(tmp_path):
    """H. Ambiguous import"""
    f1 = FileNode(id="src/a.ts", path=str(tmp_path / "src/a.ts"), name="a.ts")
    f2 = FileNode(id="src/utils.ts", path=str(tmp_path / "src/utils.ts"), name="utils.ts")
    f3 = FileNode(id="src/utils.js", path=str(tmp_path / "src/utils.js"), name="utils.js")
    
    resolver = WorkspaceResolver([f1, f2, f3], str(tmp_path))
    meta = ParsedMetadata(imports=[ImportData(module="./utils")])
    deps = resolver.resolve(f1, meta)
    
    assert len(deps) == 1
    assert deps[0].target_id == "./utils"
    assert deps[0].type == "ambiguous"

def test_python_relative_resolution(tmp_path):
    """I. Python relative import resolution"""
    f1 = FileNode(id="pkg/module.py", path=str(tmp_path / "pkg/module.py"), name="module.py")
    f2 = FileNode(id="pkg/utils.py", path=str(tmp_path / "pkg/utils.py"), name="utils.py")
    
    resolver = WorkspaceResolver([f1, f2], str(tmp_path))
    meta = ParsedMetadata(imports=[ImportData(module=".utils")])
    deps = resolver.resolve(f1, meta)
    
    assert len(deps) == 1
    assert deps[0].target_id == "pkg/utils.py"

def test_python_external_detection(tmp_path):
    """J. Python external package detection"""
    f1 = FileNode(id="pkg/module.py", path=str(tmp_path / "pkg/module.py"), name="module.py")
    
    resolver = WorkspaceResolver([f1], str(tmp_path))
    meta = ParsedMetadata(imports=[ImportData(module="pandas")])
    deps = resolver.resolve(f1, meta)
    
    assert len(deps) == 1
    assert deps[0].target_id == "pandas"

def test_graph_builder_creation():
    """K. GraphBuilder creates expected nx.DiGraph"""
    f1 = FileNode(id="a.py", path="a.py", name="a.py", dependencies=[
        Dependency(target_id="b.py", type="import"),
        Dependency(target_id="pandas", type="external"),
        Dependency(target_id="not-found", type="unresolved"),
        Dependency(target_id="ambiguous-target", type="ambiguous")
    ])
    f2 = FileNode(id="b.py", path="b.py", name="b.py")
    
    builder = GraphBuilder()
    domain_model = builder.build([f1, f2])
    
    assert "a.py" in builder.nx_graph.nodes
    assert "b.py" in builder.nx_graph.nodes
    assert not builder.nx_graph.has_node("pandas")
    assert not builder.nx_graph.has_node("not-found")
    assert not builder.nx_graph.has_node("ambiguous-target")
    
    edges = list(builder.nx_graph.edges)
    assert len(edges) == 1
    assert edges[0] == ("a.py", "b.py")

