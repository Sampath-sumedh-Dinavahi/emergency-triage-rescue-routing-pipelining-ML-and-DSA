from typing import Dict, List, Tuple

class Graph:
    """
    Weighted adjacency-list representation of the road network.
    """
    def __init__(self):
        # adjacency list: node -> {neighbor -> {"weight": float, "original_weight": float, "blocked": bool}}
        self.adj: Dict[str, Dict[str, dict]] = {}

    def add_edge(self, u: str, v: str, weight: float, bidirectional: bool = True):
        """Adds a weighted edge between node u and v."""
        if u not in self.adj:
            self.adj[u] = {}
        if v not in self.adj:
            self.adj[v] = {}
            
        self.adj[u][v] = {"weight": weight, "original_weight": weight, "blocked": False}
        if bidirectional:
            self.adj[v][u] = {"weight": weight, "original_weight": weight, "blocked": False}

    def block_road(self, u: str, v: str, bidirectional: bool = True):
        """Blocks the road between u and v, making it impassable."""
        if u in self.adj and v in self.adj[u]:
            self.adj[u][v]["blocked"] = True
        if bidirectional and v in self.adj and u in self.adj[v]:
            self.adj[v][u]["blocked"] = True

    def unblock_road(self, u: str, v: str, bidirectional: bool = True):
        """Unblocks a road, restoring its original weight."""
        if u in self.adj and v in self.adj[u]:
            self.adj[u][v]["blocked"] = False
        if bidirectional and v in self.adj and u in self.adj[v]:
            self.adj[v][u]["blocked"] = False

    def get_neighbors(self, u: str) -> List[Tuple[str, float]]:
        """
        Returns a list of active (unblocked) neighbors for node u
        as tuples of (neighbor_id, weight).
        """
        if u not in self.adj:
            return []
            
        return [
            (neighbor, data["weight"]) 
            for neighbor, data in self.adj[u].items() 
            if not data["blocked"]
        ]
        
    def get_nodes(self) -> List[str]:
        """Returns all nodes in the graph."""
        return list(self.adj.keys())
