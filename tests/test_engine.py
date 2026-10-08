"""
Unit and integration test for ZFlow execution engine and node pipelines.
"""
import asyncio
import json
import os
import sys

# Add server directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from engine.graph import WorkflowGraph
from engine.context import ExecutionContext
from engine.runner import WorkflowRunner
from nodes.base import NodeRegistry
import nodes # register all nodes

def test_node_registry():
    registered = NodeRegistry.list_all_metadata()
    types = [n["type"] for n in registered]
    assert "input" in types
    assert "prompt" in types
    assert "llm" in types
    assert "router" in types
    assert "tool" in types
    assert "memory" in types
    assert "output" in types
    assert "code" in types
    assert "http" in types
    print(f"Verified {len(registered)} registered nodes.")

async def test_full_workflow_batch():
    flow_path = os.path.join(os.path.dirname(__file__), "..", "server", "storage", "default_flow.json")
    with open(flow_path, "r", encoding="utf-8") as f:
        flow_data = json.load(f)

    graph = WorkflowGraph.from_dict(flow_data)
    context = ExecutionContext(session_id="test_session", initial_variables={"input": "Hello ZFlow!"})
    runner = WorkflowRunner()

    result = await runner.run(graph, context)
    assert result is not None
    assert "final_output" in result
    assert result["final_output"] is not None
    assert "node_outputs" in result
    print("Batch execution result:", result["final_output"][:80], "...")

async def test_workflow_streaming():
    flow_path = os.path.join(os.path.dirname(__file__), "..", "server", "storage", "default_flow.json")
    with open(flow_path, "r", encoding="utf-8") as f:
        flow_data = json.load(f)

    graph = WorkflowGraph.from_dict(flow_data)
    context = ExecutionContext(session_id="stream_test", initial_variables={"input": "Giải thích kiến trúc"})
    runner = WorkflowRunner()

    tokens = []
    events = []
    async for event in runner.run_stream(graph, context):
        events.append(event["event"])
        if event["event"] == "token":
            tokens.append(event["data"]["token"])

    assert "status" in events
    assert "node_start" in events
    assert "token" in events
    assert "node_complete" in events
    assert "workflow_complete" in events
    assert len(tokens) > 5
    print(f"Streaming test passed with {len(tokens)} tokens generated.")

if __name__ == "__main__":
    test_node_registry()
    asyncio.run(test_full_workflow_batch())
    asyncio.run(test_workflow_streaming())
    print("\nAll ZFlow Engine tests passed successfully!")
