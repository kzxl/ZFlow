"""
Output Node for Chatbot & API Workflows.
Terminates the workflow, finalizes formatting, and maps outputs for API triggers and chat interfaces.
"""
from typing import Dict, Any
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class OutputNode(BaseNode):
    node_type = "output"
    name = "Chat Response / API Output"
    category = "output"
    description = "Final destination of the workflow. Formats output and delivers response to API callers or chat users."
    icon = "Send"

    inputs = [
        PortDef(name="response_text", data_type="any", label="Response Text / Payload", required=True)
    ]
    outputs = [
        PortDef(name="final_output", data_type="any", label="Final Output")
    ]

    config_schema = {
        "output_format": {
            "type": "select",
            "label": "Output Format",
            "options": ["text", "markdown", "raw_json"],
            "default": "markdown"
        },
        "output_key": {
            "type": "string",
            "label": "API Response Field Name",
            "default": "reply"
        },
        "prefix": {
            "type": "string",
            "label": "Response Prefix",
            "default": ""
        },
        "suffix": {
            "type": "string",
            "label": "Response Suffix",
            "default": ""
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        raw_val = inputs.get("response_text") or context.get_variable("text", "")
        prefix = config.get("prefix", "")
        suffix = config.get("suffix", "")
        fmt = config.get("output_format", "markdown")
        output_key = config.get("output_key", "reply")

        if isinstance(raw_val, (dict, list)):
            final_content = raw_val
        else:
            final_content = f"{prefix}{str(raw_val)}{suffix}".strip()

        # Store in context
        context.append_chat(role="assistant", content=str(final_content))
        context.set_variable("final_output", final_content)
        context.set_variable(output_key, final_content)

        return {
            "final_output": final_content,
            output_key: final_content
        }
