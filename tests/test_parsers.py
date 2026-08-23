import pytest
from core.models import FileNode
from parsers import ParserRegistry, ParsedMetadata

def test_registry_selection():
    """j. ParserRegistry selects the correct parser."""
    py_parser = ParserRegistry.get_parser("Python")
    assert py_parser.__class__.__name__ == "PythonParser"
    
    js_parser = ParserRegistry.get_parser("JavaScript")
    assert js_parser.__class__.__name__ == "JavaScriptParser"
    
    ts_parser = ParserRegistry.get_parser("TypeScript")
    assert ts_parser.__class__.__name__ == "TypeScriptParser"

def test_unsupported_language():
    """k. Unsupported language is handled explicitly."""
    with pytest.raises(NotImplementedError):
        ParserRegistry.get_parser("Ruby")
    with pytest.raises(ValueError):
        ParserRegistry.get_parser(None)

def test_python_parsing():
    """
    a. Python import extraction.
    b. Python function extraction.
    c. Python class extraction.
    l. Relative import strings remain unresolved/raw.
    """
    source = b'''
import sys
import os as os_mod
from .utils import helper

class MyClass:
    def method(self): pass

def my_func(): pass
    '''
    node = FileNode(id="test.py", path="test.py", name="test.py", language="Python")
    parser = ParserRegistry.get_parser("Python")
    
    meta = parser.parse(node, content=source)
    
    assert not meta.has_syntax_error
    modules = [imp.module for imp in meta.imports]
    assert "sys" in modules
    assert "os" in modules
    assert ".utils" in modules  # Remains raw unresolved
    
    assert "MyClass" in meta.classes
    assert "my_func" in meta.functions
    assert "method" in meta.functions

def test_javascript_parsing():
    """
    d. JavaScript import extraction.
    e. JavaScript export extraction.
    f. JavaScript function/class extraction.
    """
    source = b'''
import { foo } from "./utils";
import React from 'react';
import "./side-effect";
export const a = 1;
export { b } from './module';
export * from "./bar";
class A {}
function b() {}
const f = () => {}
    '''
    node = FileNode(id="test.js", path="test.js", name="test.js", language="JavaScript")
    parser = ParserRegistry.get_parser("JavaScript")
    
    meta = parser.parse(node, content=source)
    
    assert not meta.has_syntax_error
    import_mods = [imp.module for imp in meta.imports]
    assert "./utils" in import_mods
    assert "react" in import_mods
    assert "./side-effect" in import_mods
    
    export_mods = [exp.module for exp in meta.exports]
    assert "./module" in export_mods
    assert "./bar" in export_mods
    
    assert "A" in meta.classes
    assert "b" in meta.functions
    assert "f" in meta.functions

def test_typescript_parsing():
    """
    g. TypeScript import extraction.
    h. TypeScript export extraction.
    i. TypeScript function/class extraction.
    """
    source = b'''
import type { a } from './utils';
import "./side-effect";
export type { c } from './module';
export * from "./bar";
class A<T> {}
function b<T>() {}
    '''
    node = FileNode(id="test.ts", path="test.ts", name="test.ts", language="TypeScript")
    parser = ParserRegistry.get_parser("TypeScript")
    
    meta = parser.parse(node, content=source)
    
    assert not meta.has_syntax_error
    import_mods = [imp.module for imp in meta.imports]
    assert "./utils" in import_mods
    assert "./side-effect" in import_mods
    
    export_mods = [exp.module for exp in meta.exports]
    assert "./module" in export_mods
    assert "./bar" in export_mods
    
    assert "A" in meta.classes
    assert "b" in meta.functions

def test_malformed_source():
    """m. A malformed source file exposes a parse-error condition appropriately."""
    source = b'''
def my_func(
    # missing parenthesis and body
    '''
    node = FileNode(id="test.py", path="test.py", name="test.py", language="Python")
    parser = ParserRegistry.get_parser("Python")
    
    meta = parser.parse(node, content=source)
    
    # Tree-sitter still parses whatever it can, but marks it with an error node
    assert meta.has_syntax_error is True

def test_tsx_parsing():
    """Verify TSX grammar is used properly for TSX files."""
    source = b'''
import { foo } from "./utils";
const a = <div></div>;
    '''
    node = FileNode(id="test.tsx", path="test.tsx", name="test.tsx", language="TSX")
    parser = ParserRegistry.get_parser("TSX")
    meta = parser.parse(node, content=source)
    assert not meta.has_syntax_error
    assert meta.imports[0].module == "./utils"

