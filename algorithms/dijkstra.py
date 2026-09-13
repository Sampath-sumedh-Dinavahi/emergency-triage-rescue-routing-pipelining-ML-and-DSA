import heapq
from typing import Tuple, List, Optional
from data_structures.graph import Graph

def find_shortest_path(graph: Graph, start: str, end: str) -> Tuple[Optional[float], Optional[List[str]]]:
    """
    Finds the shortest path between start and end nodes using Dijkstra's algorithm.
    
    Args:
        graph: The Graph object representing the road network.
        start: The starting node ID.
        end: The target node ID.
        
    Returns:
        A tuple of (total_distance, path).
        If the target is unreachable, returns (None, None).
    """
    if start not in graph.adj or end not in graph.adj:
        return None, None
        
    # Priority queue stores (distance, current_node)
    pq = [(0.0, start)]
    
    # Distances dictionary
    distances = {node: float('inf') for node in graph.get_nodes()}
    distances[start] = 0.0
    
    # Predecessors dictionary for path reconstruction
    predecessors = {node: None for node in graph.get_nodes()}
    
    while pq:
        current_distance, current_node = heapq.heappop(pq)
        
        # We found the destination
        if current_node == end:
            # Reconstruct path
            path = []
            curr = end
            while curr is not None:
                path.append(curr)
                curr = predecessors[curr]
            return current_distance, path[::-1]
            
        # If we pulled a stale, worse distance from the heap, skip it
        if current_distance > distances[current_node]:
            continue
            
        # Check all active neighbors
        for neighbor, weight in graph.get_neighbors(current_node):
            if weight < 0:
                # Dijkstra does not handle negative weights
                raise ValueError(f"Negative edge weight encountered: {weight}")
                
            distance = current_distance + weight
            
            # If we found a shorter path to neighbor
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                predecessors[neighbor] = current_node
                heapq.heappush(pq, (distance, neighbor))
                
    # If the queue empties and we haven't returned, destination is unreachable
    return None, None
