"""
ZFlow Workflow Execution Engine.
Handles asynchronous graph execution, conditional branch dispatching, and SSE token streaming.
"""
from typing import Dict, Any, AsyncGenerator, List, Set
from collections import deque
import time
import asyncio
from engine.graph import WorkflowGraph, NodeDef, EdgeDef
from engine.context import ExecutionContext
from nodes.base import NodeRegistry, BaseNode

class WorkflowRunner:
    def __init__(self, max_steps: int = 50):
        self.max_steps = max_steps

    async def run(self, graph: WorkflowGraph, context: ExecutionContext) -> Dict[str, Any]:
        """
        Executes the workflow graph in batch mode and returns the final execution context state.
        """
        async for _ in self.run_stream(graph, context):
            pass
        return {
            "session_id": context.session_id,
            "final_output": context.get_variable("final_output"),
            "node_outputs": context.node_outputs,
            "logs": context.logs,
            "total_time_ms": round((time.time() - context.start_time) * 1000, 2)
        }

    async def run_stream(
        self, graph: WorkflowGraph, context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes the workflow graph and yields real-time Server-Sent Events (SSE) events:
        - status: graph initialization
        - node_start: beginning node execution
        - token: streaming LLM token chunks
        - node_complete: node execution finished
        - node_error: error details
        - workflow_complete: whole execution summary
        """
        yield {"event": "status", "data": {"status": "started", "session_id": context.session_id}}

        # Find entry nodes
        entry_nodes = graph.get_entry_nodes()
        if not entry_nodes:
            yield {"event": "node_error", "data": {"error": "Graph has no entry nodes."}}
            return

        ready_queue: deque[NodeDef] = deque(entry_nodes)
        executed_nodes: Set[str] = set()
        step_count = 0

        while ready_queue and step_count < self.max_steps:
            current_node = ready_queue.popleft()
            step_count += 1
            node_id = current_node.id
            node_type = current_node.type

            # Check loop counter
            loop_count = context.increment_loop(node_id)
            if loop_count > 10:
                context.log("error", f"Node '{node_id}' exceeded max loop threshold (10). Breaking cycle.", node_id)
                continue

            node_cls = NodeRegistry.get(node_type)
            if not node_cls:
                context.log("error", f"Unknown node type: '{node_type}'", node_id)
                yield {"event": "node_error", "data": {"node_id": node_id, "error": f"Unknown node type: {node_type}"}}
                continue

            node_instance: BaseNode = node_cls()

            # Resolve inputs from incoming edges
            incoming_edges = graph.get_incoming_edges(node_id)
            inputs: Dict[str, Any] = {}
            for edge in incoming_edges:
                src_outputs = context.get_node_output(edge.source)
                src_val = src_outputs.get(edge.source_handle) if isinstance(src_outputs, dict) else None
                if src_val is None and isinstance(src_outputs, dict):
                    # Fallback to first available output value if handle name didn't match exactly
                    if len(src_outputs) > 0:
                        src_val = next(iter(src_outputs.values()))
                
                target_port = edge.target_handle or "input"
                inputs[target_port] = src_val

            # Announce node start
            yield {
                "event": "node_start",
                "data": {
                    "node_id": node_id,
                    "title": current_node.title,
                    "type": node_type,
                    "step": step_count
                }
            }

            node_start_time = time.time()
            collected_output: Dict[str, Any] = {}

            try:
                # Stream or execute node
                async for chunk in node_instance.execute_stream(inputs, current_node.config, context):
                    chunk_type = chunk.get("type")
                    if chunk_type == "token":
                        yield {
                            "event": "token",
                            "data": {
                                "node_id": node_id,
                                "token": chunk.get("token", "")
                            }
                        }
                    elif chunk_type == "result":
                        collected_output = chunk.get("data", {})

                # If no explicit result chunk was yielded, fallback to execute()
                if not collected_output:
                    collected_output = await node_instance.execute(inputs, current_node.config, context)

                # Record node output in context
                context.record_node_output(node_id, collected_output)
                duration_ms = round((time.time() - node_start_time) * 1000, 2)

                yield {
                    "event": "node_complete",
                    "data": {
                        "node_id": node_id,
                        "type": node_type,
                        "output": collected_output,
                        "duration_ms": duration_ms
                    }
                }

                executed_nodes.add(node_id)

                # Discover downstream nodes to queue
                outgoing_edges = graph.get_outgoing_edges(node_id)
                for edge in outgoing_edges:
                    # If current node is a router or branching node, check handle matching
                    if node_type in ("router", "llm_router", "human_input", "system1_reflex", "permission_guard", "semantic_cache"):
                        active_branch = collected_output.get("active_branch")
                        if active_branch:
                            if edge.source_handle and edge.source_handle != active_branch:
                                continue # Skip non-matching branch
                        else:
                            is_matched = collected_output.get("is_matched", False)
                            if edge.source_handle == "true_branch" and not is_matched:
                                continue # Skip false branch
                            if edge.source_handle == "false_branch" and is_matched:
                                continue # Skip true branch

                    target_node = graph.get_node(edge.target)
                    if target_node and target_node not in ready_queue:
                        ready_queue.append(target_node)

            except Exception as e:
                err_msg = str(e)
                context.log("error", f"Error in node '{node_id}': {err_msg}", node_id)
                yield {
                    "event": "node_error",
                    "data": {
                        "node_id": node_id,
                        "error": err_msg
                    }
                }

        total_time_ms = round((time.time() - context.start_time) * 1000, 2)
        yield {
            "event": "workflow_complete",
            "data": {
                "session_id": context.session_id,
                "final_output": context.get_variable("final_output"),
                "total_time_ms": total_time_ms,
                "executed_count": len(executed_nodes)
            }
        }
