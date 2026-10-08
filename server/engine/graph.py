"""
ZFlow Graph Data Structure, Validation, and Topological Flow Analysis.
Supports Directed Acyclic Graphs (DAG) as well as controlled cyclic agent loops.
"""
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, deque

class NodeDef:
    def __init__(self, node_id: str, node_type: str, title: str, config: Optional[Dict[str, Any]] = None, position: Optional[Dict[str, float]] = None):
        self.id = node_id
        self.type = node_type
        self.title = title or node_type
        self.config = config or {}
        self.position = position or {"x": 0, "y": 0}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeDef":
        node_id = data.get("id")
        node_type = data.get("type", "base")
        node_data = data.get("data", {})
        title = node_data.get("title", data.get("title", node_type))
        config = node_data.get("config", data.get("config", {}))
        position = data.get("position", {"x": 0, "y": 0})
        return cls(node_id, node_type, title, config, position)


class EdgeDef:
    def __init__(self, edge_id: str, source: str, target: str, source_handle: Optional[str] = None, target_handle: Optional[str] = None):
        self.id = edge_id
        self.source = source
        self.target = target
        self.source_handle = source_handle or "output"
        self.target_handle = target_handle or "input"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EdgeDef":
        return cls(
            edge_id=data.get("id", f"{data.get('source')}->{data.get('target')}"),
            source=data.get("source"),
            target=data.get("target"),
            source_handle=data.get("sourceHandle"),
            target_handle=data.get("targetHandle")
        )


class WorkflowGraph:
    def __init__(self, nodes: List[NodeDef], edges: List[EdgeDef]):
        self.nodes: Dict[str, NodeDef] = {n.id: n for n in nodes}
        self.edges: List[EdgeDef] = edges
        
        # Outgoing edges: source_id -> List[EdgeDef]
        self.outgoing: Dict[str, List[EdgeDef]] = defaultdict(list)
        # Incoming edges: target_id -> List[EdgeDef]
        self.incoming: Dict[str, List[EdgeDef]] = defaultdict(list)
        
        for edge in edges:
            self.outgoing[edge.source].append(edge)
            self.incoming[edge.target].append(edge)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowGraph":
        raw_nodes = data.get("nodes", [])
        raw_edges = data.get("edges", [])
        nodes = [NodeDef.from_dict(n) for n in raw_nodes]
        edges = [EdgeDef.from_dict(e) for e in raw_edges]
        return cls(nodes, edges)

    def get_node(self, node_id: str) -> Optional[NodeDef]:
        return self.nodes.get(node_id)

    def get_entry_nodes(self) -> List[NodeDef]:
        """
        Finds entry nodes in the graph:
        1. Nodes with type 'input'
        2. Nodes with 0 incoming edges
        """
        input_nodes = [n for n in self.nodes.values() if n.type == "input"]
        if input_nodes:
            return input_nodes
        
        # Fallback to zero in-degree nodes
        zero_in = [n for n in self.nodes.values() if len(self.incoming[n.id]) == 0]
        return zero_in if zero_in else list(self.nodes.values())[:1]

    def get_incoming_edges(self, node_id: str) -> List[EdgeDef]:
        return self.incoming.get(node_id, [])

    def get_outgoing_edges(self, node_id: str) -> List[EdgeDef]:
        return self.outgoing.get(node_id, [])
