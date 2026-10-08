"""
Memory Node for ZFlow.
Maintains multi-turn conversation buffer, sliding window history, and context recall.
"""
from typing import Dict, Any, List
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class MemoryNode(BaseNode):
    node_type = "memory"
    name = "Conversation Memory"
    category = "memory"
    description = "Preserves dialogue state across multi-turn interactions with sliding window budgeting."
    icon = "Database"

    inputs = []
    outputs = [
        PortDef(name="chat_history", data_type="array", label="Dialogue History"),
        PortDef(name="formatted_history", data_type="string", label="Formatted String"),
        PortDef(name="turn_count", data_type="number", label="Turn Count")
    ]

    config_schema = {
        "window_size": {
            "type": "number",
            "label": "Max Turns in Window",
            "default": 6,
            "min": 1,
            "max": 50
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        window_size = int(config.get("window_size", 6))
        history: List[Dict[str, str]] = context.chat_history[-window_size:] if context.chat_history else []

        formatted_lines = []
        for msg in history:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            formatted_lines.append(f"{role}: {content}")

        formatted_str = "\n".join(formatted_lines)
        context.set_variable("chat_history_str", formatted_str)

        return {
            "chat_history": history,
            "formatted_history": formatted_str,
            "turn_count": len(history)
        }
