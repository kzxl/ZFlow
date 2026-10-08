"""
HTTP Request / Webhook Node for ZFlow.
Calls external REST APIs or webhooks and routes responses downstream.
"""
from typing import Dict, Any
import httpx
import json
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class HttpNode(BaseNode):
    node_type = "http"
    name = "HTTP Webhook"
    category = "tool"
    description = "Dispatches outbound HTTP requests (GET/POST/PUT/DELETE) to external webhooks and third-party APIs."
    icon = "Globe"

    inputs = [
        PortDef(name="trigger_data", data_type="any", label="Trigger Input", required=False),
        PortDef(name="payload", data_type="any", label="Payload Body", required=False)
    ]
    outputs = [
        PortDef(name="response_body", data_type="any", label="Response Body"),
        PortDef(name="status_code", data_type="number", label="HTTP Status"),
        PortDef(name="is_success", data_type="boolean", label="Is Success")
    ]

    config_schema = {
        "method": {
            "type": "select",
            "label": "HTTP Method",
            "options": ["GET", "POST", "PUT", "DELETE"],
            "default": "POST"
        },
        "url": {
            "type": "string",
            "label": "Endpoint URL (supports {var})",
            "default": "https://httpbin.org/post"
        },
        "headers_json": {
            "type": "textarea",
            "label": "Headers (JSON format)",
            "default": '{\n  "Content-Type": "application/json"\n}'
        },
        "body_template": {
            "type": "textarea",
            "label": "Request Body Template",
            "default": '{\n  "query": "{query}",\n  "session_id": "{session_id}"\n}'
        },
        "timeout": {
            "type": "number",
            "label": "Timeout (seconds)",
            "default": 15
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        method = config.get("method", "POST").upper()
        url_tmpl = config.get("url", "https://httpbin.org/post")
        url = context.interpolate(url_tmpl)
        timeout_sec = float(config.get("timeout", 15))

        headers_str = config.get("headers_json", "{}")
        try:
            headers = json.loads(headers_str)
        except Exception:
            headers = {}

        body_str = config.get("body_template", "")
        formatted_body = context.interpolate(body_str) if body_str else None

        json_data = None
        if formatted_body and method in ["POST", "PUT"]:
            try:
                json_data = json.loads(formatted_body)
            except Exception:
                json_data = formatted_body

        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                if method == "GET":
                    resp = await client.get(url, headers=headers)
                elif method == "POST":
                    resp = await client.post(url, headers=headers, json=json_data if isinstance(json_data, dict) else None, content=formatted_body if not isinstance(json_data, dict) else None)
                elif method == "PUT":
                    resp = await client.put(url, headers=headers, json=json_data if isinstance(json_data, dict) else None)
                elif method == "DELETE":
                    resp = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                try:
                    res_body = resp.json()
                except Exception:
                    res_body = resp.text

                is_ok = 200 <= resp.status_code < 300
                context.set_variable("http_response", res_body)

                return {
                    "response_body": res_body,
                    "status_code": resp.status_code,
                    "is_success": is_ok
                }
        except Exception as e:
            err_msg = f"HTTP request failed: {str(e)}"
            context.log("error", err_msg)
            return {
                "response_body": err_msg,
                "status_code": 500,
                "is_success": False
            }
