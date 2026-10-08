"""
Prompt Template Node.
Composes system instructions and contextual variables into formatted prompts.
"""
from typing import Dict, Any
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class PromptNode(BaseNode):
    node_type = "prompt"
    name = "Prompt Template"
    category = "prompt"
    description = "Formats system directives, instructions, and dynamic variables {var} for the LLM."
    icon = "FileText"

    inputs = [
        PortDef(name="input_text", data_type="string", label="Input Text", required=False),
        PortDef(name="context_data", data_type="any", label="Context Data", required=False)
    ]
    outputs = [
        PortDef(name="prompt", data_type="string", label="Formatted Prompt"),
        PortDef(name="system_prompt", data_type="string", label="System Directive")
    ]

    config_schema = {
        "system_template": {
            "type": "textarea",
            "label": "System Instructions",
            "default": "Bạn là trợ lý AI thông minh, hỗ trợ người dùng giải quyết vấn đề một cách ngắn gọn, chính xác."
        },
        "user_template": {
            "type": "textarea",
            "label": "User Prompt Template",
            "default": "Câu hỏi của người dùng:\n{query}\n\nDữ liệu ngữ cảnh bổ sung:\n{context_data}"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # Merge input port values into context variables temporarily for interpolation
        for k, v in inputs.items():
            if v is not None:
                context.set_variable(k, v)
        
        system_tmpl = config.get("system_template", "")
        user_tmpl = config.get("user_template", "{query}")

        formatted_system = context.interpolate(system_tmpl)
        formatted_user = context.interpolate(user_tmpl)

        context.set_variable("system_prompt", formatted_system)
        context.set_variable("prompt", formatted_user)

        return {
            "prompt": formatted_user,
            "system_prompt": formatted_system
        }
