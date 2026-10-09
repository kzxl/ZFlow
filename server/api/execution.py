"""
Workflow Execution Router.
Handles batch execution and real-time Server-Sent Events (SSE) streaming.
"""
from fastapi import APIRouter, Request, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import json

from engine.graph import WorkflowGraph
from engine.context import ExecutionContext
from engine.runner import WorkflowRunner
from engine.memory_store import memory_store
from engine.ingress_security import verify_and_audit_ingress, bind_ingress_to_context

router = APIRouter(tags=["Execution"])


class RunRequest(BaseModel):
    workflow: Dict[str, Any]
    input: str
    session_id: Optional[str] = "default_session"
    variables: Optional[Dict[str, Any]] = Field(default_factory=dict)


@router.post("/api/workflows/run")
async def run_workflow_batch(
    request: RunRequest,
    http_request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Runs the workflow in non-streaming batch mode.
    Pre-audits access token, attaches trusted session & identity, and persists dialogue turn.
    """
    identity = verify_and_audit_ingress(http_request, authorization, session_id=request.session_id)

    graph = WorkflowGraph.from_dict(request.workflow)
    variables = request.variables.copy()
    variables["input"] = request.input
    
    context = ExecutionContext(session_id=identity.session_id, initial_variables=variables)
    bind_ingress_to_context(context, identity)
    runner = WorkflowRunner()
    
    result = await runner.run(graph, context)
    
    bot_reply = result.get("final_output") or context.get_variable("reply") or context.get_variable("final_output")
    if request.input:
        memory_store.append_message(context.session_id, "user", request.input)
    if bot_reply:
        memory_store.append_message(context.session_id, "assistant", str(bot_reply))

    return result


@router.post("/api/chat/stream")
async def chat_stream(
    request: RunRequest,
    http_request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Runs the workflow with Server-Sent Events (SSE) streaming for real-time chat interactions.
    Pre-audits access token, attaches trusted session & identity.
    """
    identity = verify_and_audit_ingress(http_request, authorization, session_id=request.session_id)

    graph = WorkflowGraph.from_dict(request.workflow)
    variables = request.variables.copy()
    variables["input"] = request.input

    context = ExecutionContext(session_id=identity.session_id, initial_variables=variables)
    bind_ingress_to_context(context, identity)
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
