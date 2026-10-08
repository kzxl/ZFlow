"""
Webhook Trigger Node for ZFlow.
Serves as an event-driven entry point triggered by incoming webhooks (GitHub, Stripe, Telegram, CRMs).
Exposes the raw payload, event headers, and automatically normalizes query text for downstream nodes.
"""
from typing import Dict, Any, AsyncGenerator
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class WebhookTriggerNode(BaseNode):
    node_type = "webhook"
    name = "Webhook Trigger"
    category = "input"
    description = "Event-driven entry node triggered by HTTP webhooks from external services like GitHub, Stripe, or webhooks."
    icon = "Webhook"

    inputs = []
    outputs = [
        PortDef(name="payload", data_type="object", label="Webhook Body"),
        PortDef(name="headers", data_type="object", label="HTTP Headers"),
        PortDef(name="event", data_type="string", label="Event Name"),
        PortDef(name="query", data_type="string", label="Normalized Query")
    ]

    config_schema = {
        "hook_id": {
            "type": "string",
            "label": "Webhook ID",
            "default": "github_hook"
        },
        "secret_token": {
            "type": "password",
            "label": "Webhook Secret / Bearer (Optional)",
            "default": ""
        },
        "event_filter": {
            "type": "string",
            "label": "Event Filter (e.g. push, payment_succeeded)",
            "default": ""
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Extracts incoming webhook payload from execution context and prepares outputs.
        """
        payload = context.get_variable("webhook_payload") or context.get_variable("payload") or {}
        headers = context.get_variable("webhook_headers") or {}
        event = (
            context.get_variable("webhook_event") 
            or headers.get("x-github-event") 
            or headers.get("x-event-type") 
            or (payload.get("event") if isinstance(payload, dict) else "")
            or "webhook_event"
        )

        # Normalize query text
        query = context.get_variable("input") or context.get_variable("query")
        if not query and isinstance(payload, dict):
            for candidate_key in ["message", "text", "query", "prompt", "action", "description"]:
                if candidate_key in payload and isinstance(payload[candidate_key], str):
                    query = payload[candidate_key]
                    break
        if not query:
            query = str(payload) if payload else "Incoming webhook trigger"

        # Sync to context variables for downstream nodes
        context.set_variable("input", query)
        context.set_variable("query", query)
        context.set_variable("webhook_payload", payload)
        context.set_variable("webhook_headers", headers)
        context.set_variable("webhook_event", event)

        context.log("info", f"Webhook trigger processed event: '{event}', hook_id: '{config.get('hook_id')}'")

        return {
            "payload": payload,
            "headers": headers,
            "event": str(event),
            "query": str(query)
        }

    async def execute_stream(
        self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        res = await self.execute(inputs, config, context)
        yield {"type": "result", "data": res}
