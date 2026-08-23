import os
from pathlib import Path
from typing import List, Set
from core.models import FileNode

# Centralized configuration for the scanner
IGNORED_DIRECTORIES: Set[str] = {
    ".git", ".venv", "node_modules", "__pycache__", "dist", "build", 
    ".pytest_cache", ".idea", ".vscode", "vendor", "target", "out", 
    "coverage", "env", "venv"
}

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
            # Additional heuristic: check if it can be decoded as utf-8
            # though null byte is usually sufficient for standard binaries.
            return False
    except Exception:
        # If we can't open/read it for some reason, conservatively skip it
        return True


class WorkspaceScanner:
    """
    Scans a local directory recursively, extracting structural file metadata
    into a list of FileNode objects.
    """

    def scan(self, target_path: str) -> List[FileNode]:
        target = Path(target_path)
        
        if not target.exists():
            raise FileNotFoundError(f"Target path does not exist: {target_path}")
        
        if not target.is_dir():
            raise NotADirectoryError(f"Target path is not a directory: {target_path}")
            
        return self._traverse_directory(target)

    def _traverse_directory(self, root_dir: Path) -> List[FileNode]:
        nodes: List[FileNode] = []
        
        # We use standard library pathlib for traversal.
        # rglob handles recursive iteration safely, but we need to control 
        # filtering dynamically (e.g. ignoring node_modules).
        # We can implement a manual stack-based or queue-based traversal to prune directories efficiently.
        
        stack = [root_dir]
        
        while stack:
            current_dir = stack.pop()
            
            try:
                for entry in current_dir.iterdir():
                    if entry.is_symlink():
                        # Requirement: Skip symbolic links
                        continue
                        
                    if entry.is_dir():
                        if entry.name not in IGNORED_DIRECTORIES:
                            stack.append(entry)
                    elif entry.is_file():
                        node = self._process_file(entry, root_dir)
                        if node:
                            nodes.append(node)
            except PermissionError:
                # Skip directories we don't have permission to read
                continue
                
        return nodes

    def _process_file(self, file_path: Path, root_dir: Path) -> FileNode | None:
        """
        Creates a FileNode for a given file if it is not binary.
        Returns None if the file is binary or should be skipped.
        """
        if is_binary_file(file_path):
            return None
            
        try:
            stat = file_path.stat()
            size = stat.st_size
        except OSError:
            size = 0
            
        # Get relative path as ID, normalizing to forward slashes for cross-platform graph stability
        rel_path = file_path.relative_to(root_dir)
        node_id = rel_path.as_posix()
        
        language = EXTENSION_LANGUAGES.get(file_path.suffix.lower())
        
        # Create FileNode with known properties
        return FileNode(
            id=node_id,
            path=str(file_path.absolute()),
            name=file_path.name,
            language=language,
            size=size
        )
