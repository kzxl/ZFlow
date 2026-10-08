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
from engine.memory_store import memory_store
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
    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)

    # Check if any saved JSON file has matching internal id
    for fp in glob.glob(os.path.join(STORAGE_DIR, "*.json")):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
                if d.get("id") == flow_id:
                    return d
        except Exception:
            continue

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
    seen_ids = set()
    for filepath in glob.glob(os.path.join(STORAGE_DIR, "*.json")):
        file_stem = os.path.splitext(os.path.basename(filepath))[0]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                flow_id = data.get("id") or file_stem
                if flow_id in seen_ids:
                    flow_id = file_stem
                seen_ids.add(flow_id)
                workflows.append({
                    "id": flow_id,
                    "file_stem": file_stem,
                    "name": data.get("name", file_stem.replace("_", " ").title()),
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
    Sanitizes ID and persists to storage directory.
    """
    import re
    raw_id = payload.id or payload.name or "custom_flow"
    wf_id = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_id.strip()).lower()
    wf_id = re.sub(r'_+', '_', wf_id).strip('_') or "custom_flow"

    data = payload.model_dump()
    data["id"] = wf_id
    if not data.get("name"):
        data["name"] = wf_id.replace("_", " ").title()

    target = os.path.join(STORAGE_DIR, f"{wf_id}.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {"status": "saved", "id": wf_id, "name": data.get("name")}


@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """
    Deletes a saved workflow from storage (protects default_flow.json).
    """
    if workflow_id in ["default_flow"]:
        raise HTTPException(status_code=400, detail="Cannot delete default system starter template.")
    target = os.path.join(STORAGE_DIR, f"{workflow_id}.json")
    if os.path.exists(target):
        os.remove(target)
        return {"status": "deleted", "id": workflow_id}
    raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")


@app.post("/api/workflows/run")
async def run_workflow_batch(request: RunRequest):
    """
    Runs the workflow in non-streaming batch mode.
    Auto-persists dialogue turn to SQLite session memory.
    """
    graph = WorkflowGraph.from_dict(request.workflow)
    variables = request.variables.copy()
    variables["input"] = request.input
    
    context = ExecutionContext(session_id=request.session_id, initial_variables=variables)
    runner = WorkflowRunner()
    
    result = await runner.run(graph, context)
    
    bot_reply = result.get("final_output") or context.get_variable("reply") or context.get_variable("final_output")
    if request.input:
        memory_store.append_message(context.session_id, "user", request.input)
    if bot_reply:
        memory_store.append_message(context.session_id, "assistant", str(bot_reply))

    return result


@app.post("/api/chat/stream")
async def chat_stream(request: RunRequest):
    """
    Runs the workflow with Server-Sent Events (SSE) streaming for real-time chat interactions.
    Yields tokens, node transitions, and completion payloads.
    Auto-persists dialogue turn to SQLite session memory upon completion.
    """
    graph = WorkflowGraph.from_dict(request.workflow)
    variables = request.variables.copy()
    variables["input"] = request.input

    context = ExecutionContext(session_id=request.session_id, initial_variables=variables)
    runner = WorkflowRunner()

    async def event_generator():
        bot_tokens = []
        final_output = None
        try:
            async for sse_event in runner.run_stream(graph, context):
                event_name = sse_event.get("event", "message")
                data = sse_event.get("data", {})
                
                if event_name == "token":
                    bot_tokens.append(data.get("token", ""))
                elif event_name == "workflow_complete":
                    final_output = data.get("final_output")

                data_str = json.dumps(data, ensure_ascii=False)
                yield f"event: {event_name}\ndata: {data_str}\n\n"

            # Auto-save conversation turn upon successful stream
            bot_reply = final_output or "".join(bot_tokens) or context.get_variable("reply") or context.get_variable("final_output")
            if request.input:
                memory_store.append_message(context.session_id, "user", request.input)
            if bot_reply:
                memory_store.append_message(context.session_id, "assistant", str(bot_reply))

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

    user_q = initial_vars.get("input")
    if user_q:
        memory_store.append_message(session_id, "user", str(user_q))
    if custom_reply:
        memory_store.append_message(session_id, "assistant", str(custom_reply))

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
        bot_tokens = []
        final_output = None
        try:
            async for sse_event in runner.run_stream(graph, context):
                event_name = sse_event.get("event", "message")
                data = sse_event.get("data", {})
                
                if event_name == "token":
                    bot_tokens.append(data.get("token", ""))
                elif event_name == "workflow_complete":
                    final_output = data.get("final_output")

                data_str = json.dumps(data, ensure_ascii=False)
                yield f"event: {event_name}\ndata: {data_str}\n\n"

            # Auto-save conversation turn upon successful stream
            bot_reply = final_output or "".join(bot_tokens) or context.get_variable("reply") or context.get_variable("final_output")
            user_q = initial_vars.get("input")
            if user_q:
                memory_store.append_message(session_id, "user", str(user_q))
            if bot_reply:
                memory_store.append_message(session_id, "assistant", str(bot_reply))

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
# 🧠 Conversation Memory & SQLite Store REST Endpoints
# =========================================================================

@app.get("/api/memory/sessions")
async def list_memory_sessions():
    """
    Returns list of all conversation sessions stored in SQLite with stats and message previews.
    """
    return {"sessions": memory_store.list_sessions()}


@app.get("/api/memory/sessions/{session_id}")
async def get_session_history(session_id: str):
    """
    Retrieves chronological dialogue history and statistics for a specific session.
    """
    history = memory_store.get_history(session_id)
    stats = memory_store.get_session_stats(session_id)
    return {
        "session_id": session_id,
        "stats": stats,
        "history": history
    }


@app.delete("/api/memory/sessions/{session_id}")
async def clear_session_memory(session_id: str):
    """
    Clears all persistent conversation turns for a session from SQLite.
    """
    memory_store.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.post("/api/memory/sessions/{session_id}/clear")
async def clear_session_memory_post(session_id: str):
    """
    Alternative POST endpoint for clearing session memory.
    """
    memory_store.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/api/memory/sessions/{session_id}/stats")
async def get_session_stats_endpoint(session_id: str):
    """
    Retrieves turn counts, estimated tokens, and message breakdown for a session.
    """
    return memory_store.get_session_stats(session_id)


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
