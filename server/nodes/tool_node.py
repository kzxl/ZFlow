"""
Tool Node for ZFlow.
Executes functions like Safe Math Calculation, Web Search, Current Datetime, or HTTP API calls.
"""
from typing import Dict, Any
import datetime
import math
import httpx
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class ToolNode(BaseNode):
    node_type = "tool"
    name = "Tool Executor"
    category = "tool"
    description = "Invokes functional tools (Math Calculator, Web Search, Time/Date, or Custom HTTP APIs)."
    icon = "Wrench"

    inputs = [
        PortDef(name="input_arg", data_type="string", label="Tool Input / Argument", required=False)
    ]
    outputs = [
        PortDef(name="result", data_type="string", label="Tool Output"),
        PortDef(name="status", data_type="string", label="Execution Status")
    ]

    config_schema = {
        "tool_name": {
            "type": "select",
            "label": "Selected Tool",
            "options": ["calculator", "datetime_now", "web_search", "http_api"],
            "default": "datetime_now"
        },
        "api_endpoint": {
            "type": "string",
            "label": "Custom API Endpoint (if http_api)",
            "default": "https://api.github.com"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        tool_name = config.get("tool_name", "datetime_now")
        arg = str(inputs.get("input_arg") or context.get_variable("user_query", ""))

        result_str = ""
        status = "success"

        try:
            if tool_name == "datetime_now":
                now = datetime.datetime.now()
                result_str = now.strftime("%Y-%m-%d %H:%M:%S (Thứ %w, Giờ địa phương)")
            
            elif tool_name == "calculator":
                # Safe math evaluator
                allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
                # Extract math expr from string or use direct arg
                clean_expr = arg.replace("^", "**")
                val = eval(clean_expr, {"__builtins__": None}, allowed_names)
                result_str = str(val)

            elif tool_name == "web_search":
                # Simulated search summary for arg
                result_str = (
                    f"Kết quả tìm kiếm cho '{arg}':\n"
                    f"1. ZeroUniverse và hệ sinh thái ZFlow: Nền tảng điều phối AI Workflow thuần khiết.\n"
                    f"2. Công nghệ SSE Streaming giúp tối ưu hóa TTFT dưới 50ms cho người dùng cuối.\n"
                    f"3. Node-based Visual Canvas cho phép gắn các Option và cấu hình trực quan."
                )

            elif tool_name == "http_api":
                endpoint = config.get("api_endpoint", "https://api.github.com")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(endpoint)
                    result_str = resp.text[:1000]

        except Exception as e:
            status = "error"
            result_str = f"Lỗi thực thi Tool '{tool_name}': {str(e)}"

        context.set_variable("tool_result", result_str)
        context.log("info", f"Tool '{tool_name}' executed with status {status}")

        return {
            "result": result_str,
            "status": status
        }
