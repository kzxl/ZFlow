"""
Output Node for Chatbot Workflows.
Terminates the workflow, finalizes formatting, and appends the assistant answer to session memory.
"""
from typing import Dict, Any
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class OutputNode(BaseNode):
    node_type = "output"
    name = "Chat Response"
    category = "output"
    description = "Final destination of the workflow. Delivers the answer to the user and stores assistant turn."
    icon = "Send"

    inputs = [
        PortDef(name="response_text", data_type="string", label="Response Text", required=True)
    ]
    outputs = [
        PortDef(name="final_output", data_type="string", label="Final Output")
    ]

    config_schema = {
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
        text = str(inputs.get("response_text") or context.get_variable("text", ""))
        prefix = config.get("prefix", "")
        suffix = config.get("suffix", "")

        final_content = f"{prefix}{text}{suffix}".strip()
        context.append_chat(role="assistant", content=final_content)
        context.set_variable("final_output", final_content)

        return {
            "final_output": final_content
        }
