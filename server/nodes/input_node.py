"""
User Input Node for Chatbot Workflows.
Captures user query, session variables, and conversation metadata.
"""
from typing import Dict, Any
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext
import time

@NodeRegistry.register
class InputNode(BaseNode):
    node_type = "input"
    name = "User Input"
    category = "input"
    description = "Starting point of the chatbot workflow. Receives incoming user query and session metadata."
    icon = "MessageSquare"

    inputs = []
    outputs = [
        PortDef(name="query", data_type="string", label="User Query", description="The text input sent by the user"),
        PortDef(name="session_id", data_type="string", label="Session ID", description="Unique conversation session key"),
        PortDef(name="timestamp", data_type="number", label="Timestamp", description="Epoch timestamp of the request")
    ]

    config_schema = {
        "placeholder": {
            "type": "string",
            "label": "Input Placeholder",
            "default": "Type your message here..."
        },
        "default_query": {
            "type": "string",
            "label": "Default Test Query",
            "default": "Xin chào! Bạn có thể giúp gì cho tôi?"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        # User query comes from context.variables['input'] or config fallback
        query = context.get_variable("input")
        if query is None or query == "":
            query = config.get("default_query", "Xin chào!")
        
        # Save user query to chat history
        context.append_chat(role="user", content=query)
        context.set_variable("user_query", query)
        
        return {
            "query": query,
            "session_id": context.session_id,
            "timestamp": time.time()
        }
