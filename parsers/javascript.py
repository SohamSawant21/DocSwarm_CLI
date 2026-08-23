from typing import Optional
from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_javascript
from core.models import FileNode
from parsers.base import LanguageParser, ParsedMetadata, ImportData, ExportData

JS_LANGUAGE = Language(tree_sitter_javascript.language())

JS_QUERY_STR = """
(import_statement source: (string) @import)
(export_statement source: (string) @export)
(class_declaration name: (identifier) @class)
(function_declaration name: (identifier) @function)
(variable_declarator name: (identifier) @function value: (arrow_function))
"""
JS_QUERY = Query(JS_LANGUAGE, JS_QUERY_STR)

class JavaScriptParser(LanguageParser):
    def __init__(self):
        self.parser = Parser(JS_LANGUAGE)
        
    def parse(self, file_node: FileNode, content: Optional[bytes] = None) -> ParsedMetadata:
        if content is None:
            with open(file_node.path, 'rb') as f:
                content = f.read()
                
        tree = self.parser.parse(content)
        has_error = tree.root_node.has_error
        
        meta = ParsedMetadata(has_syntax_error=has_error)
        
        cursor = QueryCursor(JS_QUERY)
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
