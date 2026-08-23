from typing import Protocol, List, Optional
from pydantic import BaseModel, Field
from core.models import FileNode

class ImportData(BaseModel):
    module: str
    names: List[str] = Field(default_factory=list)

class ExportData(BaseModel):
    module: Optional[str] = None
    names: List[str] = Field(default_factory=list)

class ParsedMetadata(BaseModel):
    """Structured syntax metadata extracted from a source file."""
    has_syntax_error: bool = False
    imports: List[ImportData] = Field(default_factory=list)
    exports: List[ExportData] = Field(default_factory=list)
    classes: List[str] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)

class LanguageParser(Protocol):
    """Protocol for language-specific parsers."""
    
    def parse(self, file_node: FileNode, content: Optional[bytes] = None) -> ParsedMetadata:
        """
        Parses the source code of a FileNode.
        If `content` is provided, it parses the in-memory bytes (useful for testing).
        Otherwise, it explicitly reads the file from `file_node.path`.
        """
        ...
