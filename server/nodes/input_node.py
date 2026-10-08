"""
User Input Node for Chatbot Workflows.
Captures user query, session variables, and conversation metadata.
"""
import json
import time
from typing import Dict, Any
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class InputNode(BaseNode):
    node_type = "input"
    name = "User Input"
    category = "input"
    description = "Starting point of the workflow. Receives incoming user query, structured JSON payloads, task types, and session metadata."
    icon = "MessageSquare"

    inputs = []
    outputs = [
        PortDef(name="query", data_type="string", label="User Query", description="Normalized text representation of the request"),
        PortDef(name="payload", data_type="object", label="Raw / Parsed Payload", description="Full structured JSON payload or dictionary"),
        PortDef(name="task_type", data_type="string", label="Task Type / Purpose", description="Purpose identifier e.g. chat, data_pipeline, media_gen, webhook"),
        PortDef(name="metadata", data_type="object", label="Envelope Metadata", description="Envelope metadata including headers, source, and tenant ID"),
        PortDef(name="session_id", data_type="string", label="Session ID", description="Unique conversation session key"),
        PortDef(name="access_token", data_type="string", label="Access Token (JWT)", description="Bearer access token passed via request headers or parameters"),
        PortDef(name="timestamp", data_type="number", label="Timestamp", description="Epoch timestamp of the request")
    ]

    config_schema = {
        "placeholder": {
            "type": "string",
            "label": "Input Placeholder",
            "default": "Type your message or JSON payload here..."
        },
        "default_query": {
            "type": "string",
            "label": "Default Test Query",
            "default": "Xin chào! Bạn có thể giúp gì cho tôi?"
        },
        "default_task_type": {
            "type": "string",
            "label": "Default Task Type",
            "default": "chat"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        raw_input = context.get_variable("input")
        if raw_input is None or raw_input == "":
            raw_input = context.get_variable("payload")
        if raw_input is None or raw_input == "":
            raw_input = config.get("default_query", "Xin chào!")

        payload: Dict[str, Any] = {}
        task_type = config.get("default_task_type", "chat")
        query_text = ""

        # 1. Parse structured payload if JSON string or dictionary
        if isinstance(raw_input, dict):
            payload = raw_input
        elif isinstance(raw_input, str) and (raw_input.strip().startswith("{") or raw_input.strip().startswith("[")):
            try:
                parsed = json.loads(raw_input)
                if isinstance(parsed, dict):
                    payload = parsed
                else:
                    payload = {"items": parsed}
            except Exception:
                payload = {"text": raw_input}
        else:
            payload = {"text": str(raw_input)}

        # 2. Extract task_type from payload, context, or config
        if isinstance(payload, dict):
            task_type = (
                payload.get("task_type")
                or payload.get("purpose")
                or payload.get("action")
                or context.get_variable("task_type")
                or config.get("default_task_type", "chat")
            )
            # Extract query candidate
            for key in ["query", "message", "prompt", "text", "description"]:
                if key in payload and isinstance(payload[key], str):
                    query_text = payload[key]
                    break
            if not query_text:
                query_text = str(raw_input) if isinstance(raw_input, str) else json.dumps(payload, ensure_ascii=False)
        else:
            query_text = str(raw_input)

        # 3. Extract metadata
        meta = context.get_variable("metadata") or {}
        if isinstance(payload, dict) and "metadata" in payload and isinstance(payload["metadata"], dict):
            meta.update(payload["metadata"])
        meta.setdefault("session_id", context.session_id)
        meta.setdefault("source", "user_input")

        # 4. Save user query to chat history if it is a conversational request
        if task_type in ["chat", "conversational", "auto"] and query_text:
            context.append_chat(role="user", content=query_text)

        # 5. Extract access token
        access_token = (
            context.get_variable("access_token")
            or context.get_variable("token")
            or str(context.get_variable("webhook_headers", {}).get("authorization", "")).replace("Bearer ", "").strip()
            or ""
        )

        # 6. Synchronize into context variables for downstream nodes
        context.set_variable("query", query_text)
        context.set_variable("user_query", query_text)
        context.set_variable("payload", payload)
        context.set_variable("task_type", task_type)
        context.set_variable("metadata", meta)
        context.set_variable("access_token", access_token)

        return {
            "query": query_text,
            "payload": payload,
            "task_type": task_type,
            "metadata": meta,
            "session_id": context.session_id,
            "access_token": access_token,
            "timestamp": time.time()
        }
