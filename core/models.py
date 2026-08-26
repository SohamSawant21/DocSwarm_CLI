from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Dependency(BaseModel):
    """Represents a dependency between two files/nodes."""
    target_id: str
    type: str = "import"  # e.g., 'import', 'dynamic_import', etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FileNode(BaseModel):
    """Represents a parsed file in the codebase."""
    id: str  # Unique identifier, usually the relative path
    path: str
    name: str
    language: Optional[str] = None
    role: str = "Other"
    size: int = 0
    imports: List[str] = Field(default_factory=list)
    dependencies: List[Dependency] = Field(default_factory=list)
    file_hash: Optional[str] = None
    
    # Custom metadata or analysis results
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GraphModel(BaseModel):
    """Represents the complete architecture graph of the codebase."""
    nodes: Dict[str, FileNode] = Field(default_factory=dict)
    
    def add_node(self, node: FileNode) -> None:
        self.nodes[node.id] = node
        
    def add_dependency(self, source_id: str, dependency: Dependency) -> None:
        if source_id in self.nodes:
            self.nodes[source_id].dependencies.append(dependency)
            
    def get_edges(self) -> List[Dict[str, str]]:
        edges = []
        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                edges.append({
                    "source": node_id,
                    "target": dep.target_id,
                    "type": dep.type
                })
        return edges

class ParsingReport(BaseModel):
    """Tracks errors and skips during the analysis pipeline."""
    skipped_binary: List[str] = Field(default_factory=list)
    skipped_oversized: List[str] = Field(default_factory=list)
    syntax_errors: List[str] = Field(default_factory=list)
    parser_exceptions: Dict[str, str] = Field(default_factory=dict)

class AnalysisResult(BaseModel):
    """Result of the complete analysis pipeline."""
    graph: GraphModel
    analysis: Any = None # Will be ArchitectureAnalysis, use Any to avoid circular import or define it here
    parsing_report: ParsingReport = Field(default_factory=ParsingReport)
