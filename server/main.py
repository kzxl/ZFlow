"""
ZFlow Backend Server (FastAPI).
Provides REST endpoints and Server-Sent Events (SSE) streaming for chatbot workflow execution.
Includes first-class Public Flow API triggers for external applications.
"""
from fastapi import FastAPI, HTTPException, Request, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import os
import glob
import asyncio
import time
import uuid

from engine.graph import WorkflowGraph
from engine.context import ExecutionContext
from engine.runner import WorkflowRunner
from nodes.base import NodeRegistry
import nodes # trigger registration of all nodes

app = FastAPI(
    title="ZFlow — Sovereign Chatbot Workflow Engine",
    description="Node-based visual workflow & orchestration API for AI chatbots.",
    version="1.1.0"
)

# Enable CORS for Frontend dev server and local access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

class WorkflowPayload(BaseModel):
    id: Optional[str] = "custom_flow"
    name: Optional[str] = "Untitled Flow"
    description: Optional[str] = ""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)

class RunRequest(BaseModel):
    workflow: Dict[str, Any]
    input: str
    session_id: Optional[str] = "default_session"
    variables: Optional[Dict[str, Any]] = Field(default_factory=dict)

class FlowExecuteRequest(BaseModel):
    inputs: Dict[str, Any] = Field(
        default_factory=lambda: {"query": "Hello ZFlow!"},
        description="Dictionary of input variables passed into the workflow (e.g. {'query': 'Hello'})"
    )
    session_id: Optional[str] = Field(default=None, description="Optional conversation session ID")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional parameter overrides")


def load_flow_data(flow_id: str) -> Dict[str, Any]:
    """Helper to locate and parse workflow JSON from storage."""
    target = os.path.join(STORAGE_DIR, f"{flow_id}.json")
    if not os.path.exists(target):
        # Fallback to default_flow.json
        target = os.path.join(STORAGE_DIR, "default_flow.json")
        if not os.path.exists(target):
            raise HTTPException(status_code=404, detail=f"Workflow '{flow_id}' not found.")

    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": "ZFlow",
        "registered_nodes": len(NodeRegistry.list_all_metadata()),
        "version": "1.1.0"
    }


@app.get("/api/nodes")
async def get_node_definitions():
    """
    Returns list of all registered node types, their inputs/outputs ports and configuration schema.
    Used by the Frontend canvas to populate the node sidebar palette.
    """
    return {"nodes": NodeRegistry.list_all_metadata()}


@app.get("/api/workflows")
async def list_workflows():
    """
    Lists saved workflows in the local storage directory.
    """
    workflows = []
    for filepath in glob.glob(os.path.join(STORAGE_DIR, "*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                workflows.append({
                    "id": data.get("id", os.path.splitext(os.path.basename(filepath))[0]),
                    "name": data.get("name", "Unnamed Flow"),
                    "description": data.get("description", ""),
                    "node_count": len(data.get("nodes", [])),
                    "edge_count": len(data.get("edges", []))
                })
        except Exception:
            continue
    return {"workflows": workflows}


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """
    Retrieves full workflow JSON definition.
    """
    return load_flow_data(workflow_id)


@app.post("/api/workflows")
async def save_workflow(payload: WorkflowPayload):
    """
    Saves or updates a workflow JSON definition.
    """
    wf_id = payload.id or "flow_saved"
    target = os.path.join(STORAGE_DIR, f"{wf_id}.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload.model_dump(), f, indent=2, ensure_ascii=False)
    return {"status": "saved", "id": wf_id}


@app.post("/api/workflows/run")
async def run_workflow_batch(request: RunRequest):
    """
    Runs the workflow in non-streaming batch mode.
    """
    graph = WorkflowGraph.from_dict(request.workflow)
    variables = request.variables.copy()
    variables["input"] = request.input
    
    context = ExecutionContext(session_id=request.session_id, initial_variables=variables)
    runner = WorkflowRunner()
    
    result = await runner.run(graph, context)
    return result


@app.post("/api/chat/stream")
async def chat_stream(request: RunRequest):
    """
    Runs the workflow with Server-Sent Events (SSE) streaming for real-time chat interactions.
    Yields tokens, node transitions, and completion payloads.
    """
    graph = WorkflowGraph.from_dict(request.workflow)
    variables = request.variables.copy()
    variables["input"] = request.input

    context = ExecutionContext(session_id=request.session_id, initial_variables=variables)
    runner = WorkflowRunner()

    async def event_generator():
        try:
            async for sse_event in runner.run_stream(graph, context):
                event_name = sse_event.get("event", "message")
                data_str = json.dumps(sse_event.get("data", {}), ensure_ascii=False)
                yield f"event: {event_name}\ndata: {data_str}\n\n"
        except Exception as e:
            err_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {err_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# =========================================================================
# 🚀 First-Class Public Flow API Endpoints (Auto-Trigger by Flow ID)
# =========================================================================

@app.post("/api/v1/flows/{flow_id}/run")
async def trigger_flow_api(
    flow_id: str = Path(..., description="ID of the saved workflow to execute"),
    request: FlowExecuteRequest = FlowExecuteRequest()
):
    """
    Public API trigger: Automatically loads and executes a workflow by flow_id.
    Accepts external inputs and returns structured JSON outputs synchronously.
    """
    flow_data = load_flow_data(flow_id)
    graph = WorkflowGraph.from_dict(flow_data)

    # Resolve inputs and session
    session_id = request.session_id or f"api_sess_{uuid.uuid4().hex[:8]}"
    initial_vars = request.parameters.copy()
    initial_vars.update(request.inputs)
    
    # Map primary query input if present
    if "query" in request.inputs:
        initial_vars["input"] = request.inputs["query"]
    elif "input" in request.inputs:
        initial_vars["input"] = request.inputs["input"]

    context = ExecutionContext(session_id=session_id, initial_variables=initial_vars)
    runner = WorkflowRunner()

    start_t = time.time()
    result = await runner.run(graph, context)
    total_time_ms = round((time.time() - start_t) * 1000, 2)

    # Format outputs
    final_output = result.get("final_output")
    custom_reply = context.get_variable("reply") or final_output

    return {
        "status": "success",
        "flow_id": flow_id,
        "flow_name": flow_data.get("name", flow_id),
        "session_id": session_id,
        "outputs": {
            "reply": custom_reply,
            "final_output": final_output,
            "all_variables": context.variables
        },
        "execution_time_ms": total_time_ms,
        "logs": context.logs
    }


@app.post("/api/v1/flows/{flow_id}/stream")
async def trigger_flow_stream_api(
    flow_id: str = Path(..., description="ID of the saved workflow to stream"),
    request: FlowExecuteRequest = FlowExecuteRequest()
):
    """
    Public API trigger: Automatically loads and executes a workflow with real-time SSE token streaming.
    Ideal for external Chatbots, Web apps, Discord/Telegram bots.
    """
    flow_data = load_flow_data(flow_id)
    graph = WorkflowGraph.from_dict(flow_data)

    session_id = request.session_id or f"api_sess_{uuid.uuid4().hex[:8]}"
    initial_vars = request.parameters.copy()
    initial_vars.update(request.inputs)
    
    if "query" in request.inputs:
        initial_vars["input"] = request.inputs["query"]
    elif "input" in request.inputs:
        initial_vars["input"] = request.inputs["input"]

    context = ExecutionContext(session_id=session_id, initial_variables=initial_vars)
    runner = WorkflowRunner()

    async def event_generator():
        try:
            async for sse_event in runner.run_stream(graph, context):
                event_name = sse_event.get("event", "message")
                data_str = json.dumps(sse_event.get("data", {}), ensure_ascii=False)
                yield f"event: {event_name}\ndata: {data_str}\n\n"
        except Exception as e:
            err_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {err_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/v1/flows/{flow_id}/schema")
async def get_flow_io_schema(flow_id: str = Path(...)):
    """
    Returns the Input and Output signature of a workflow so external developers
    know exactly what inputs to provide and what outputs will be returned.
    """
    flow_data = load_flow_data(flow_id)
    nodes_list = flow_data.get("nodes", [])

    inputs_schema = []
    outputs_schema = []

    for n in nodes_list:
        n_type = n.get("type")
        n_title = n.get("data", {}).get("title", n.get("title", n_type))
        if n_type in ["input", "webhook"]:
            inputs_schema.append({
                "node_id": n.get("id"),
                "node_title": n_title,
                "expected_fields": ["query", "input"]
            })
        elif n_type in ["output"]:
            output_key = n.get("data", {}).get("config", {}).get("output_key", "reply")
            outputs_schema.append({
                "node_id": n.get("id"),
                "node_title": n_title,
                "output_fields": ["final_output", output_key]
            })

    return {
        "flow_id": flow_id,
        "flow_name": flow_data.get("name", flow_id),
        "endpoint_run": f"/api/v1/flows/{flow_id}/run",
        "endpoint_stream": f"/api/v1/flows/{flow_id}/stream",
        "inputs": inputs_schema,
        "outputs": outputs_schema
    }


# Mount static build from web/dist if present for seamless single-server deployment
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "dist"))
if os.path.exists(DIST_DIR):
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
