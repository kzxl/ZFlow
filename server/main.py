"""
ZFlow Backend Server (FastAPI).
Provides REST endpoints and Server-Sent Events (SSE) streaming for chatbot workflow execution.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import os
import glob
import asyncio

from engine.graph import WorkflowGraph
from engine.context import ExecutionContext
from engine.runner import WorkflowRunner
from nodes.base import NodeRegistry
import nodes # trigger registration of all nodes

app = FastAPI(
    title="ZFlow — Sovereign Chatbot Workflow Engine",
    description="Node-based visual workflow & orchestration API for AI chatbots.",
    version="1.0.0"
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


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "ZFlow", "registered_nodes": len(NodeRegistry.list_all_metadata())}


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
    target = os.path.join(STORAGE_DIR, f"{workflow_id}.json")
    if not os.path.exists(target):
        # Check default flow fallback
        target = os.path.join(STORAGE_DIR, "default_flow.json")
        if not os.path.exists(target):
            raise HTTPException(status_code=404, detail="Workflow not found")

    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


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

# Mount static build from web/dist if present for seamless single-server deployment
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "dist"))
if os.path.exists(DIST_DIR):
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
