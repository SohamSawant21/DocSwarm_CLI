from .base import LanguageParser, ParsedMetadata, ImportData, ExportData
from .registry import ParserRegistry
from .python import PythonParser
from .javascript import JavaScriptParser
from .typescript import TypeScriptParser, TSXParser

# Register built-in parsers
ParserRegistry.register("Python", PythonParser())
ParserRegistry.register("JavaScript", JavaScriptParser())
ParserRegistry.register("TypeScript", TypeScriptParser())
ParserRegistry.register("JSX", JavaScriptParser())  # Treat JSX as JS for now
ParserRegistry.register("TSX", TSXParser())

__all__ = [
    "LanguageParser", 
    "ParsedMetadata", 
    "ImportData", 
    "ExportData", 
    "ParserRegistry"
]
