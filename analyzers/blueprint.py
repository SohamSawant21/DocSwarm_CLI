from typing import Dict, Any
import networkx as nx
from core.models import GraphModel

class BlueprintGenerator:
    """
    Generates architectural blueprints from the parsed codebase graph.
    Adapted from the original DocSwarm backend.
    """
    
    @staticmethod
    def generate_repo_map(graph_model: GraphModel, nx_graph: nx.DiGraph, project_overview: str = "No README found.") -> str:
        blueprint = "### REPOSITORY ARCHITECTURE BLUEPRINT\n\n"
        
        # 1. Project Overview
        blueprint += f"#### 1. PROJECT OVERVIEW\n{project_overview}\n\n"
        
        # 2. Architectural Roles
        roles = {
            "Entry Points": [],
            "Routing & Controllers": [],
            "Data Models & Persistence": [],
            "Services & Utilities": [],
            "UI Components": [],
            "Configuration": [],
            "Documentation": []
        }
        
        for node_id, node in graph_model.nodes.items():
            role = node.role
            if role in roles:
                roles[role].append(node_id)
                
        blueprint += "#### 2. ARCHITECTURAL ROLES\n"
        for role, paths in roles.items():
            if paths:
                file_list = ", ".join(paths[:10]) + ("..." if len(paths) > 10 else "")
                blueprint += f"- **{role}**: {file_list}\n"
        blueprint += "\n"
        
        # 3. Logical Dependency Graph (Top Relationships)
        blueprint += "#### 3. LOGICAL DEPENDENCY GRAPH (TOP RELATIONSHIPS)\n"
        edges = list(nx_graph.edges())
        for u, v in edges[:20]:
            blueprint += f"- `{u}` --> depends on --> `{v}`\n"
        if len(edges) > 20:
            blueprint += f"- ... (total {len(edges)} relationships)\n"
        blueprint += "\n"
        
        # 4. Directory Tree
        blueprint += "#### 4. DIRECTORY TREE\n"
        dirs = set()
        for path in graph_model.nodes.keys():
            parts = path.split('/')
            if len(parts) > 1:
                dirs.add(f"- {parts[0]}/")
                if len(parts) > 2:
                    dirs.add(f"  - {parts[0]}/{parts[1]}/")
        
        blueprint += "\n".join(sorted(list(dirs))[:30])
        
        return blueprint
