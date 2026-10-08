"""
Public Flow API Router.
Enables external applications, Discord/Telegram bots, and webhooks to trigger workflows by Flow ID.
"""
from fastapi import APIRouter, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import json
import time
import uuid

from engine.graph import WorkflowGraph
from engine.context import ExecutionContext
from engine.runner import WorkflowRunner
from engine.memory_store import memory_store
from .workflows import load_flow_data

router = APIRouter(tags=["Public Flow API"])


class FlowExecuteRequest(BaseModel):
    inputs: Dict[str, Any] = Field(
        default_factory=lambda: {"query": "Hello ZFlow!"},
        description="Dictionary of input variables passed into the workflow (e.g. {'query': 'Hello'})"
    )
    session_id: Optional[str] = Field(default=None, description="Optional conversation session ID")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional parameter overrides")


@router.post("/api/v1/flows/{flow_id}/run")
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

    session_id = request.session_id or f"api_sess_{uuid.uuid4().hex[:8]}"
    initial_vars = request.parameters.copy()
    initial_vars.update(request.inputs)
    
    if "query" in request.inputs:
        initial_vars["input"] = request.inputs["query"]
    elif "input" in request.inputs:
        initial_vars["input"] = request.inputs["input"]

    context = ExecutionContext(session_id=session_id, initial_variables=initial_vars)
    runner = WorkflowRunner()

    start_t = time.time()
    result = await runner.run(graph, context)
    total_time_ms = round((time.time() - start_t) * 1000, 2)

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


@router.post("/api/v1/flows/{flow_id}/stream")
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


@router.get("/api/v1/flows/{flow_id}/schema")
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
