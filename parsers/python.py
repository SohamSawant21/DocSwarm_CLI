from typing import Optional
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_python
from core.models import FileNode
from parsers.base import LanguageParser, ParsedMetadata, ImportData

PY_LANGUAGE = Language(tree_sitter_python.language())

PY_QUERY_STR = """
(import_statement (dotted_name) @import)
(import_statement (aliased_import name: (dotted_name) @import))
(import_from_statement module_name: (_) @from_import)
(class_definition name: (identifier) @class)
(function_definition name: (identifier) @function)
"""
PY_QUERY = Query(PY_LANGUAGE, PY_QUERY_STR)

class PythonParser(LanguageParser):
    def __init__(self):
        self.parser = Parser(PY_LANGUAGE)
        
    def parse(self, file_node: FileNode, content: Optional[bytes] = None) -> ParsedMetadata:
        if content is None:
            with open(file_node.path, 'rb') as f:
                content = f.read()
                
        tree = self.parser.parse(content)
        has_error = tree.root_node.has_error
        
        meta = ParsedMetadata(has_syntax_error=has_error)
        
        cursor = QueryCursor(PY_QUERY)
        captures = cursor.captures(tree.root_node)
        
        # Merge imports
        imports = captures.get('import', [])
        from_imports = captures.get('from_import', [])
        
        for imp in imports:
            mod_name = imp.text.decode('utf-8')
            meta.imports.append(ImportData(module=mod_name))
            
        for imp in from_imports:
            mod_name = imp.text.decode('utf-8')
            meta.imports.append(ImportData(module=mod_name))
            
        # Classes
        classes = captures.get('class', [])
        for c in classes:
            meta.classes.append(c.text.decode('utf-8'))
            
        # Functions
        functions = captures.get('function', [])
        for f in functions:
            meta.functions.append(f.text.decode('utf-8'))
            
        return meta
