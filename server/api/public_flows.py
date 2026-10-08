"""
Public Flow API Router.
Enables external applications, Discord/Telegram bots, and webhooks to trigger workflows by Flow ID
or via the special 'active' alias (targeting the currently designated active workflow).
"""
from fastapi import APIRouter, Path, Request, HTTPException, Query
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
from engine.settings_manager import settings_manager
from .workflows import load_flow_data

router = APIRouter(tags=["Public Flow API"])


class FlowExecuteRequest(BaseModel):
    inputs: Dict[str, Any] = Field(
        default_factory=lambda: {"query": "Hello ZFlow!"},
        description="Dictionary of input variables passed into the workflow (e.g. {'query': 'Hello', 'user_role': 'staff'})"
    )
    session_id: Optional[str] = Field(default=None, description="Optional conversation session ID")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional parameter overrides")


def resolve_target_flow(flow_id: str):
    """
    Resolves workflow data. If flow_id is 'active', seamlessly routes
    to the system's currently active workflow.
    """
    actual_flow_id = flow_id
    if flow_id.lower() == "active":
        actual_flow_id = settings_manager.get("active_flow_id", "default_flow")
    
    flow_data = load_flow_data(actual_flow_id)
    return actual_flow_id, flow_data


def extract_workflow_outputs(graph: WorkflowGraph, context: ExecutionContext, final_output: Any) -> Dict[str, Any]:
    """
    Extracts all declared outputs from every Output Node in the graph.
    Ensures callers receive exactly the keys defined by the workflow.
    """
    outputs_map: Dict[str, Any] = {}
    
    # 1. Primary fallbacks
    primary_reply = context.get_variable("reply") or final_output
    if primary_reply is not None:
        outputs_map["reply"] = primary_reply
    if final_output is not None:
        outputs_map["final_output"] = final_output

    # 2. Extract specific output_key from every output node in the graph
    for node in graph.nodes.values():
        if node.type == "output":
            cfg = node.config or {}
            out_key = cfg.get("output_key", "reply")
            node_out = context.get_node_output(node.id)
            if isinstance(node_out, dict) and out_key in node_out:
                outputs_map[out_key] = node_out[out_key]
            elif context.get_variable(out_key) is not None:
                outputs_map[out_key] = context.get_variable(out_key)

    # 3. Add all variables for comprehensive inspection
    outputs_map["all_variables"] = context.variables
    return outputs_map


@router.post("/api/v1/flows/{flow_id}/run")
async def trigger_flow_api(
    flow_id: str = Path(..., description="ID of the workflow to execute, or 'active' for the currently active workflow"),
    request: FlowExecuteRequest = FlowExecuteRequest()
):
    """
    Public API trigger: Automatically loads and executes a workflow by flow_id or 'active'.
    Maps external input variables and returns structured JSON outputs according to the active workflow.
    """
    resolved_id, flow_data = resolve_target_flow(flow_id)
    graph = WorkflowGraph.from_dict(flow_data)

    session_id = request.session_id or f"api_sess_{uuid.uuid4().hex[:8]}"
    initial_vars = request.parameters.copy()
    initial_vars.update(request.inputs)
    
    # Standardize primary user query across common variable aliases
    if "query" in request.inputs:
        initial_vars["input"] = request.inputs["query"]
        initial_vars["query"] = request.inputs["query"]
    elif "input" in request.inputs:
        initial_vars["input"] = request.inputs["input"]
        initial_vars["query"] = request.inputs["input"]

    context = ExecutionContext(session_id=session_id, initial_variables=initial_vars)
    runner = WorkflowRunner()

    start_t = time.time()
    result = await runner.run(graph, context)
    total_time_ms = round((time.time() - start_t) * 1000, 2)

    final_output = result.get("final_output")
    outputs_dict = extract_workflow_outputs(graph, context, final_output)

    user_q = initial_vars.get("input")
    primary_reply = outputs_dict.get("reply") or outputs_dict.get("final_output")
    if user_q:
        memory_store.append_message(session_id, "user", str(user_q))
    if primary_reply:
        memory_store.append_message(session_id, "assistant", str(primary_reply))

    return {
        "status": "success",
        "flow_id": resolved_id,
        "is_active_route": (flow_id.lower() == "active"),
        "flow_name": flow_data.get("name", resolved_id),
        "session_id": session_id,
        "outputs": outputs_dict,
        "node_outputs": context.node_outputs,
        "execution_time_ms": total_time_ms,
        "logs": context.logs
    }


@router.post("/api/v1/flows/{flow_id}/stream")
async def trigger_flow_stream_api(
    flow_id: str = Path(..., description="ID of the workflow to stream, or 'active' for the currently active workflow"),
    request: FlowExecuteRequest = FlowExecuteRequest()
):
    """
    Public API trigger: Automatically loads and executes a workflow with real-time SSE token streaming.
    Supports 'active' alias to always stream the currently active workflow.
    """
    resolved_id, flow_data = resolve_target_flow(flow_id)
    graph = WorkflowGraph.from_dict(flow_data)

    session_id = request.session_id or f"api_sess_{uuid.uuid4().hex[:8]}"
    initial_vars = request.parameters.copy()
    initial_vars.update(request.inputs)
    
    if "query" in request.inputs:
        initial_vars["input"] = request.inputs["query"]
        initial_vars["query"] = request.inputs["query"]
    elif "input" in request.inputs:
        initial_vars["input"] = request.inputs["input"]
        initial_vars["query"] = request.inputs["input"]

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


@router.get("/api/v1/flows/{flow_id}/schema")
async def get_flow_io_schema(
    flow_id: str = Path(..., description="ID of the workflow, or 'active'")
):
    """
    Returns the Input and Output signature of a workflow so external developers
    know exactly what inputs to provide and what outputs will be returned.
    """
    resolved_id, flow_data = resolve_target_flow(flow_id)
    nodes_list = flow_data.get("nodes", [])

    inputs_schema = []
    outputs_schema = []

    for n in nodes_list:
        n_type = n.get("type")
        n_title = n.get("data", {}).get("title", n.get("title", n_type))
        if n_type in ["input", "webhook"]:
            cfg = n.get("data", {}).get("config", {})
            inputs_schema.append({
                "node_id": n.get("id"),
                "node_title": n_title,
                "node_type": n_type,
                "default_query": cfg.get("default_query", ""),
                "expected_fields": ["query", "input", "user_role", "session_id"]
            })
        elif n_type in ["output"]:
            cfg = n.get("data", {}).get("config", {})
            out_key = cfg.get("output_key", "reply")
            outputs_schema.append({
                "node_id": n.get("id"),
                "node_title": n_title,
                "output_key": out_key,
                "output_fields": ["reply", "final_output", out_key]
            })

    return {
        "flow_id": resolved_id,
        "is_active_route": (flow_id.lower() == "active"),
        "flow_name": flow_data.get("name", resolved_id),
        "endpoint_run": f"/api/v1/flows/{flow_id}/run",
        "endpoint_stream": f"/api/v1/flows/{flow_id}/stream",
        "inputs": inputs_schema,
        "outputs": outputs_schema
    }


@router.post("/api/v1/webhook/{hook_id}")
async def handle_incoming_webhook(
    hook_id: str = Path(..., description="Unique Webhook identifier configured on the WebhookTriggerNode"),
    flow_id: Optional[str] = Query(None, description="Optional target workflow ID or 'active'"),
    request: Request = None
):
    """
    Event-driven Webhook receiver:
    Accepts external webhook payloads (GitHub, Stripe, custom events) and triggers the corresponding workflow.
    Validates secret tokens if configured on the WebhookTriggerNode.
    """
    # 1. Parse JSON payload or fallback to raw bytes text
    payload: Dict[str, Any] = {}
    try:
        payload = await request.json()
    except Exception:
        raw_body = await request.body()
        if raw_body:
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception:
                payload = {"raw_text": raw_body.decode("utf-8", errors="ignore")}

    headers_dict = dict(request.headers)
    incoming_secret = (
        headers_dict.get("x-webhook-secret") 
        or headers_dict.get("authorization", "").replace("Bearer ", "").strip()
        or request.query_params.get("secret", "")
    )

    # 2. Determine target workflow
    target_flow_id = flow_id or "active"
    resolved_id, flow_data = resolve_target_flow(target_flow_id)
    graph = WorkflowGraph.from_dict(flow_data)

    # 3. Check for WebhookTriggerNode and validate secret token if configured
    webhook_node_found = False
    for node in graph.nodes.values():
        if node.type == "webhook":
            cfg = node.config or {}
            cfg_hook_id = str(cfg.get("hook_id", "")).strip()
            # If node config specifies hook_id, verify match
            if cfg_hook_id and cfg_hook_id != hook_id:
                continue

            webhook_node_found = True
            expected_secret = str(cfg.get("secret_token", "")).strip()
            if expected_secret and incoming_secret != expected_secret:
                raise HTTPException(status_code=401, detail="Invalid webhook secret token.")

    session_id = f"hook_{hook_id}_{uuid.uuid4().hex[:8]}"

    # 4. Extract query message from payload
    extracted_query = ""
    for candidate_key in ["message", "text", "query", "prompt", "comment", "action"]:
        if isinstance(payload, dict) and candidate_key in payload and isinstance(payload[candidate_key], str):
            extracted_query = payload[candidate_key]
            break
    if not extracted_query:
        extracted_query = f"Webhook event received for hook_id '{hook_id}'"

    initial_vars = {
        "input": extracted_query,
        "query": extracted_query,
        "webhook_payload": payload,
        "webhook_headers": headers_dict,
        "webhook_event": headers_dict.get("x-github-event") or headers_dict.get("x-event-type") or payload.get("event") or hook_id,
        "webhook_id": hook_id
    }

    context = ExecutionContext(session_id=session_id, initial_variables=initial_vars)
    runner = WorkflowRunner(max_steps=50)

    try:
        exec_result = await runner.run(graph, context)
        final_output = exec_result.get("final_output")
        extracted_outputs = extract_workflow_outputs(graph, context, final_output)

        return {
            "status": "success",
            "hook_id": hook_id,
            "flow_id": resolved_id,
            "session_id": session_id,
            "total_time_ms": exec_result.get("total_time_ms", 0),
            "outputs": extracted_outputs,
            "benchmarks": exec_result.get("benchmarks", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook workflow execution failed: {str(e)}")
