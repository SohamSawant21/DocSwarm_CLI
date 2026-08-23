from typing import Optional
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_typescript
from core.models import FileNode
from parsers.base import LanguageParser, ParsedMetadata, ImportData, ExportData

TS_LANGUAGE = Language(tree_sitter_typescript.language_typescript())

TS_QUERY_STR = """
(import_statement source: (string) @import)
(export_statement source: (string) @export)
(class_declaration name: [(type_identifier) (identifier)] @class)
(function_declaration name: (identifier) @function)
(variable_declarator name: (identifier) @function value: (arrow_function))
"""
TS_QUERY = Query(TS_LANGUAGE, TS_QUERY_STR)

class TypeScriptParser(LanguageParser):
    def __init__(self):
        self.parser = Parser(TS_LANGUAGE)
        
    def parse(self, file_node: FileNode, content: Optional[bytes] = None) -> ParsedMetadata:
        if content is None:
            with open(file_node.path, 'rb') as f:
                content = f.read()
                
        tree = self.parser.parse(content)
        has_error = tree.root_node.has_error
        
        meta = ParsedMetadata(has_syntax_error=has_error)
        
        cursor = QueryCursor(TS_QUERY)
        captures = cursor.captures(tree.root_node)
        
        imports = captures.get('import', [])
        for imp in imports:
            mod_name = imp.text.decode('utf-8').strip("'\"")
            meta.imports.append(ImportData(module=mod_name))
            
        exports = captures.get('export', [])
        for exp in exports:
            mod_name = exp.text.decode('utf-8').strip("'\"")
            meta.exports.append(ExportData(module=mod_name))
            
        classes = captures.get('class', [])
        for c in classes:
            meta.classes.append(c.text.decode('utf-8'))
            
        functions = captures.get('function', [])
        for f in functions:
            meta.functions.append(f.text.decode('utf-8'))
            
        return meta

TSX_LANGUAGE = Language(tree_sitter_typescript.language_tsx())
TSX_QUERY = Query(TSX_LANGUAGE, TS_QUERY_STR)

class TSXParser(LanguageParser):
    def __init__(self):
        self.parser = Parser(TSX_LANGUAGE)
        
    def parse(self, file_node: FileNode, content: Optional[bytes] = None) -> ParsedMetadata:
        if content is None:
            with open(file_node.path, 'rb') as f:
                content = f.read()
                
        tree = self.parser.parse(content)
        has_error = tree.root_node.has_error
        
        meta = ParsedMetadata(has_syntax_error=has_error)
        
        cursor = QueryCursor(TSX_QUERY)
        captures = cursor.captures(tree.root_node)
        
        imports = captures.get('import', [])
        for imp in imports:
            mod_name = imp.text.decode('utf-8').strip("'\"")
            meta.imports.append(ImportData(module=mod_name))
            
        exports = captures.get('export', [])
        for exp in exports:
            mod_name = exp.text.decode('utf-8').strip("'\"")
            meta.exports.append(ExportData(module=mod_name))
            
        classes = captures.get('class', [])
        for c in classes:
            meta.classes.append(c.text.decode('utf-8'))
            
        functions = captures.get('function', [])
        for f in functions:
            meta.functions.append(f.text.decode('utf-8'))
            
        return meta

