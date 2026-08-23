import networkx as nx
from typing import List, Dict
from core.models import GraphModel, FileNode

class GraphBuilder:
    """
    Constructs the NetworkX DiGraph and populated GraphModel 
    from a list of FileNodes whose dependencies have been resolved.
    """
    
    def __init__(self):
        self.nx_graph = nx.DiGraph()
        self.domain_model = GraphModel()
        
    def build(self, file_nodes: List[FileNode]) -> GraphModel:
        """
        Populates the graph explicitly obeying the rule:
        ONLY create edges for fully resolved internal dependencies.
        """
        # 1. Add all valid internal nodes first
        for node in file_nodes:
            self.domain_model.add_node(node)
            self.nx_graph.add_node(
                node.id, 
                label=node.name, 
                language=node.language,
                role=node.role
            )
            
        # 2. Add edges for resolved internal dependencies
        for node in file_nodes:
            for dep in node.dependencies:
                # Rule: DO NOT INVENT EDGES. 
                # Only "import" type (resolved internal edges) are added to the graph.
                # "external", "unresolved", and "ambiguous" deps are kept in the domain model 
                # but NOT added as edges in the nx_graph to prevent false internal connections.
                if dep.type == "import" and dep.target_id in self.domain_model.nodes:
                    self.nx_graph.add_edge(node.id, dep.target_id)
                    # We also register it in the GraphModel structure if required by other phases,
                    # though it's already in the node.dependencies.
                    
        return self.domain_model
