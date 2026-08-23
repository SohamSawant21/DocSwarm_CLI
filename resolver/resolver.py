import os
import json
import re
from typing import List, Dict, Set, Optional, Any
from pathlib import Path

from core.models import FileNode, Dependency
from parsers.base import ParsedMetadata, ImportData

class WorkspaceResolver:
    """
    Resolves raw module strings into internal file dependencies.
    """
    def __init__(self, workspace_files: List[FileNode], workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.files_by_id: Dict[str, FileNode] = {f.id: f for f in workspace_files}
        self.file_ids = set(self.files_by_id.keys())
        self.tsconfig = self._load_tsconfig()

    def _load_tsconfig(self) -> Dict[str, Any]:
        tsconfig_path = self.workspace_root / "tsconfig.json"
        if tsconfig_path.exists():
            try:
                text = tsconfig_path.read_text(encoding='utf-8')
                # Strip comments for simple JSON parsing
                text = re.sub(r'//.*', '', text)
                text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
                return json.loads(text)
            except Exception:
                pass
        return {}

    def resolve(self, source_node: FileNode, metadata: ParsedMetadata) -> List[Dependency]:
        deps: List[Dependency] = []
        is_python = source_node.id.endswith('.py')
        
        # Combine imports and exports for dependency tracking
        all_modules = []
        for imp in metadata.imports:
            all_modules.append(imp.module)
        for exp in metadata.exports:
            if exp.module:
                all_modules.append(exp.module)
                
        # Deduplicate
        seen = set()
        for mod in all_modules:
            if mod in seen:
                continue
            seen.add(mod)
            dep = self._resolve_import(source_node, mod, is_python)
            deps.append(dep)
            
        return deps

    def _resolve_import(self, source_node: FileNode, module_str: str, is_python: bool) -> Dependency:
        if is_python:
            return self._resolve_python(source_node, module_str)
        else:
            return self._resolve_js_ts(source_node, module_str)
            
    def _resolve_python(self, source_node: FileNode, module_str: str) -> Dependency:
        candidates = []
        
        if module_str.startswith('.'):
            dots = 0
            for char in module_str:
                if char == '.':
                    dots += 1
                else:
                    break
            
            parts = source_node.id.split('/')[:-1]
            levels_up = dots - 1
            if levels_up <= len(parts):
                base_parts = parts[:len(parts) - levels_up] if levels_up > 0 else parts
                base_path = '/'.join(base_parts)
                rest = module_str[dots:].replace('.', '/')
                if rest:
                    candidate_base = f"{base_path}/{rest}" if base_path else rest
                else:
                    candidate_base = base_path
                    
                candidates.append(candidate_base + ".py")
                candidates.append(candidate_base + "/__init__.py")
        else:
            candidate_base = module_str.replace('.', '/')
            candidates.append(candidate_base + ".py")
            candidates.append(candidate_base + "/__init__.py")
            
        matched = [c for c in candidates if c in self.file_ids]
        
        if len(matched) == 1:
            return Dependency(target_id=matched[0], type="import")
        elif len(matched) > 1:
            return Dependency(target_id=module_str, type="ambiguous", metadata={"reason": "Multiple internal matches"})
        else:
            return Dependency(target_id=module_str, type="external", metadata={"reason": "External package or unresolvable"})

    def _resolve_js_ts(self, source_node: FileNode, module_str: str) -> Dependency:
        candidates = []
        source_dir = os.path.dirname(source_node.id)
        # Normalize to forward slashes
        source_dir = source_dir.replace('\\', '/')
        
        if module_str.startswith('.'):
            raw_path = f"{source_dir}/{module_str}" if source_dir else module_str
            parts = []
            for p in raw_path.split('/'):
                if p == '..':
                    if parts: parts.pop()
                elif p != '.' and p != '':
                    parts.append(p)
            base_path = '/'.join(parts)
            candidates.extend(self._generate_js_ts_candidates(base_path))
        else:
            alias_path = self._resolve_tsconfig_alias(module_str)
            if alias_path:
                candidates.extend(self._generate_js_ts_candidates(alias_path))
            else:
                return Dependency(target_id=module_str, type="external", metadata={"reason": "External package"})
                
        matched = [c for c in candidates if c in self.file_ids]
        
        if len(matched) == 1:
            return Dependency(target_id=matched[0], type="import")
        elif len(matched) > 1:
            return Dependency(target_id=module_str, type="ambiguous", metadata={"reason": "Multiple internal matches"})
        else:
            return Dependency(target_id=module_str, type="unresolved", metadata={"reason": "Not found in workspace"})
            
    def _generate_js_ts_candidates(self, base_path: str) -> List[str]:
        candidates = [base_path]
        exts = ['.ts', '.tsx', '.js', '.jsx', '.json']
        for ext in exts:
            candidates.append(f"{base_path}{ext}")
        for ext in exts:
            candidates.append(f"{base_path}/index{ext}")
        return candidates
        
    def _resolve_tsconfig_alias(self, module_str: str) -> Optional[str]:
        if not self.tsconfig:
            return None
            
        compiler_options = self.tsconfig.get("compilerOptions", {})
        paths = compiler_options.get("paths", {})
        base_url = compiler_options.get("baseUrl", ".")
        
        if base_url == ".":
            base_url = ""
        elif base_url.startswith("./"):
            base_url = base_url[2:]
            
        for alias, targets in paths.items():
            if not targets:
                continue
            
            if alias.endswith("*"):
                prefix = alias[:-1]
                if module_str.startswith(prefix):
                    suffix = module_str[len(prefix):]
                    target = targets[0].replace("*", suffix)
                    res = f"{base_url}/{target}" if base_url else target
                    # Normalize slashes
                    res = re.sub(r'/+', '/', res)
                    return res
            else:
                if module_str == alias:
                    target = targets[0]
                    res = f"{base_url}/{target}" if base_url else target
                    res = re.sub(r'/+', '/', res)
                    return res
                    
        return None
