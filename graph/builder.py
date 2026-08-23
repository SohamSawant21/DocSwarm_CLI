import os
import re
import networkx as nx
from typing import Dict, Any, List, Set, Tuple
from core.models import GraphModel, Dependency

class GraphBuilder:
    """
    Handles construction and manipulation of the NetworkX graph and the core GraphModel.
    Adapted and modularized from the old DocSwarm graph_service.py.
    """
    
    def __init__(self):
        self.nx_graph = nx.DiGraph()
        self.domain_model = GraphModel()
        
    def add_node(self, node_id: str, label: str, metadata: Dict[str, Any] = None):
        """Adds a node to both the NetworkX graph and the domain model."""
        if metadata is None:
            metadata = {}
            
        self.nx_graph.add_node(node_id, label=label, type="customNode", **metadata)
        # Note: the actual FileNode object should be created and added to domain_model
        # by the caller (Parser), but we provide a hook here.
        
    def build_edges_from_imports(self, node_id: str, imports: List[str], existing_files: Set[str]):
        """
        Attempts to resolve import strings to actual file nodes and creates edges.
        Includes heuristics for resolving Node.js and Python import paths.
        """
        node_dir = os.path.dirname(node_id)
        is_python = node_id.endswith('.py')
        
        # Pre-build lookup map for O(1) fallback resolution
        suffix_map = self._build_suffix_map(existing_files)
        
        for imp in imports:
            resolved_targets = []
            
            if is_python:
                clean_imp = imp.replace('.', '/')
                resolved_targets.append(clean_imp)
            else:
                if imp.startswith('.'):
                    resolved_path = os.path.normpath(os.path.join(node_dir, imp)).replace('\\', '/')
                    resolved_targets.append(resolved_path)
                else:
                    clean_imp = re.sub(r'^[@~]/?', '', imp)
                    resolved_targets.append(clean_imp)
            
            found_target = self._resolve_target(resolved_targets, existing_files)
            
            if found_target:
                self._add_edge(node_id, found_target)
            else:
                # Optimized fallback heuristic
                fallback_target = self._fallback_resolve(imp, is_python, suffix_map)
                if fallback_target:
                    self._add_edge(node_id, fallback_target)
                    
    def _add_edge(self, source: str, target: str):
        self.nx_graph.add_edge(source, target)
        if source in self.domain_model.nodes:
            self.domain_model.add_dependency(source, Dependency(target_id=target))

    def _build_suffix_map(self, existing_files: Set[str]) -> Dict[str, str]:
        suffix_map = {}
        for target_id in existing_files:
            target_id_no_ext = os.path.splitext(target_id)[0]
            parts = target_id_no_ext.split('/')
            for i in range(len(parts)):
                suffix = "/".join(parts[i:])
                if suffix not in suffix_map:
                    suffix_map[suffix] = target_id
                
                if target_id_no_ext.endswith("/index") and not target_id.endswith(".py"):
                    if suffix.endswith("/index"):
                        dir_suffix = suffix[:-6]
                        if dir_suffix and dir_suffix not in suffix_map:
                            suffix_map[dir_suffix] = target_id
                elif target_id_no_ext.endswith("/__init__") and target_id.endswith(".py"):
                    if suffix.endswith("/__init__"):
                        dir_suffix = suffix[:-9]
                        if dir_suffix and dir_suffix not in suffix_map:
                            suffix_map[dir_suffix] = target_id
        return suffix_map

    def _resolve_target(self, resolved_targets: List[str], existing_files: Set[str]) -> str:
        for target_base in resolved_targets:
            if target_base in existing_files:
                return target_base
            
            possible_paths = [
                f"{target_base}.js", f"{target_base}.ts", 
                f"{target_base}.jsx", f"{target_base}.tsx",
                f"{target_base}.mjs", f"{target_base}.cjs",
                f"{target_base}.py",
                f"{target_base}/index.js", f"{target_base}/index.ts", 
                f"{target_base}/index.jsx", f"{target_base}/index.tsx",
                f"{target_base}/__init__.py"
            ]
            
            for p in possible_paths:
                if p in existing_files:
                    return p
        return None

    def _fallback_resolve(self, imp: str, is_python: bool, suffix_map: Dict[str, str]) -> str:
        if is_python:
            clean_imp = imp.replace('.', '/')
        else:
            clean_imp = re.sub(r'^(\./|\.\./)+', '', imp)
            clean_imp = re.sub(r'^[@~]/?', '', clean_imp)
            clean_imp = re.sub(r'\.(js|ts|jsx|tsx|mjs|cjs|py)$', '', clean_imp)
        
        return suffix_map.get(clean_imp)
