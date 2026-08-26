import os
from pathlib import Path
from typing import List, Set, Optional
import pathspec
from core.models import FileNode
from core.config import ScannerConfig

MANDATORY_IGNORES = [".docswarm", ".git"]

# Centralized extension-to-language mapping
EXTENSION_LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JSX",
    ".tsx": "TSX",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".css": "CSS",
    ".html": "HTML",
    ".htm": "HTML"
}

def is_binary_file(file_path: Path) -> bool:
    """
    Checks if a file is binary by attempting to read its first 1024 bytes
    and looking for a null byte (\\0).
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return True
            return False
    except Exception:
        return True


class WorkspaceScanner:
    """
    Scans a local directory recursively, extracting structural file metadata
    into a list of FileNode objects.
    """

    def __init__(self, config: Optional[ScannerConfig] = None):
        # We handle the legacy max_file_size_kb parameter for backward compatibility if instantiated dynamically,
        # but since AnalysisService now instantiates WorkspaceScanner() with no args, it relies on this defaults fallback.
        # Wait, the prompt says "preserve backward compatibility when .docswarm.yaml is absent".
        # AnalysisService does `WorkspaceScanner(self.config.scanner)`. Let's assume it gets passed.
        self.config = config or ScannerConfig()
        self.skipped_binary: List[str] = []
        self.skipped_oversized: List[str] = []
        self.spec: Optional[pathspec.PathSpec] = None

    def scan(self, target_path: str) -> List[FileNode]:
        target = Path(target_path)
        
        if not target.exists():
            raise FileNotFoundError(f"Target path does not exist: {target_path}")
        
        if not target.is_dir():
            raise NotADirectoryError(f"Target path is not a directory: {target_path}")
            
        # 1. Load .gitignore if present
        gitignore_path = target / ".gitignore"
        gitignore_patterns = []
        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                gitignore_patterns = f.read().splitlines()
                
        # 2. Combine with custom_excludes
        # We don't include MANDATORY_IGNORES in pathspec because we handle them at the directory entry level for speed
        combined_patterns = gitignore_patterns + self.config.custom_excludes
        self.spec = pathspec.PathSpec.from_lines('gitignore', combined_patterns)
            
        return self._traverse_directory(target)

    def _traverse_directory(self, root_dir: Path) -> List[FileNode]:
        nodes: List[FileNode] = []
        stack = [root_dir]
        
        while stack:
            current_dir = stack.pop()
            
            try:
                for entry in current_dir.iterdir():
                    if entry.is_symlink():
                        continue
                        
                    rel_path = entry.relative_to(root_dir).as_posix()
                    
                    if entry.is_dir():
                        # Mandatory ignores bypass pathspec entirely
                        if entry.name in MANDATORY_IGNORES:
                            continue
                        
                        # Match directory against pathspec (requires trailing slash per pathspec convention)
                        if self.spec.match_file(rel_path + "/"):
                            continue
                            
                        stack.append(entry)
                    elif entry.is_file():
                        if self.spec.match_file(rel_path):
                            continue
                            
                        node = self._process_file(entry, root_dir)
                        if node:
                            nodes.append(node)
            except PermissionError:
                continue
                
        return nodes

    def _process_file(self, file_path: Path, root_dir: Path) -> FileNode | None:
        rel_path = file_path.relative_to(root_dir)
        node_id = rel_path.as_posix()

        if is_binary_file(file_path):
            self.skipped_binary.append(node_id)
            return None
            
        try:
            stat = file_path.stat()
            size = stat.st_size
        except OSError:
            size = 0
            
        if self.config.max_file_size_kb is not None and size > self.config.max_file_size_kb * 1024:
            self.skipped_oversized.append(node_id)
            return None
        
        language = EXTENSION_LANGUAGES.get(file_path.suffix.lower())
        
        return FileNode(
            id=node_id,
            path=str(file_path.absolute()),
            name=file_path.name,
            language=language,
            size=size
        )
