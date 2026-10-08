"""
Conversation Memory Node for ZFlow.
Maintains multi-turn conversation history with 4 distinct memory strategies:
1. sliding_window: Keeps last N dialogue turns.
2. token_budget: Truncates oldest turns to strictly stay within max token budget.
3. summary_buffer: Summarizes older dialog while keeping recent window intact.
4. full_history: Preserves entire session history.
"""
from typing import Dict, Any, List
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext
from engine.memory_store import memory_store

@NodeRegistry.register
class MemoryNode(BaseNode):
    node_type = "memory"
    name = "Conversation Memory"
    category = "memory"
    description = "Retrieves and formats multi-turn dialogue history with sliding window and token budgeting."
    icon = "Database"

    inputs = [
        PortDef(name="session_id", data_type="string", label="Session ID (Optional)", required=False),
        PortDef(name="user_message", data_type="string", label="New User Msg (Optional)", required=False),
        PortDef(name="bot_message", data_type="string", label="New Bot Msg (Optional)", required=False)
    ]
    outputs = [
        PortDef(name="chat_history", data_type="array", label="Dialogue History (Array)"),
        PortDef(name="formatted_history", data_type="string", label="Formatted String"),
        PortDef(name="turn_count", data_type="number", label="Turn Count"),
        PortDef(name="summary", data_type="string", label="Context Summary")
    ]

    config_schema = {
        "strategy": {
            "type": "select",
            "label": "Memory Strategy",
            "options": ["sliding_window", "token_budget", "summary_buffer", "full_history"],
            "default": "sliding_window"
        },
        "window_size": {
            "type": "number",
            "label": "Window Size (Recent Turns)",
            "default": 6,
            "min": 1,
            "max": 50,
            "step": 1
        },
        "max_token_budget": {
            "type": "number",
            "label": "Max Token Budget",
            "default": 2048,
            "min": 256,
            "max": 16384,
            "step": 128
        },
        "storage_backend": {
            "type": "select",
            "label": "Storage Backend",
            "options": ["sqlite_persistent", "in_memory"],
            "default": "sqlite_persistent"
        },
        "human_prefix": {
            "type": "string",
            "label": "Human Speaker Prefix",
            "default": "User"
        },
        "ai_prefix": {
            "type": "string",
            "label": "AI Assistant Prefix",
            "default": "Assistant"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        session_id = inputs.get("session_id") or context.session_id or "default_session"
        strategy = config.get("strategy", "sliding_window")
        window_size = int(config.get("window_size", 6))
        token_budget = int(config.get("max_token_budget", 2048))
        use_sqlite = config.get("storage_backend", "sqlite_persistent") == "sqlite_persistent"
        human_prefix = config.get("human_prefix", "User")
        ai_prefix = config.get("ai_prefix", "Assistant")

        # Explicit message injection if passed via ports
        user_msg = inputs.get("user_message")
        bot_msg = inputs.get("bot_message")

        if user_msg:
            memory_store.append_message(session_id, "user", str(user_msg), use_sqlite=use_sqlite)
        if bot_msg:
            memory_store.append_message(session_id, "assistant", str(bot_msg), use_sqlite=use_sqlite)

        # Retrieve raw history from persistent store
        raw_history = memory_store.get_history(session_id, use_sqlite=use_sqlite)
        
        # If execution context already had in-flight history, merge them
        if not raw_history and context.chat_history:
            raw_history = context.chat_history

        active_history: List[Dict[str, Any]] = []
        summary_text = ""

        # Apply Memory Strategy
        if strategy == "sliding_window":
            active_history = raw_history[-window_size:] if len(raw_history) > window_size else raw_history

        elif strategy == "token_budget":
            # Rough token estimate: ~4 chars per token
            budget_chars = token_budget * 4
            running_chars = 0
            selected_reversed = []
            for msg in reversed(raw_history):
                chars = len(msg.get("content", ""))
                if running_chars + chars <= budget_chars:
                    selected_reversed.append(msg)
                    running_chars += chars
                else:
                    break
            active_history = list(reversed(selected_reversed))

        elif strategy == "summary_buffer":
            if len(raw_history) > window_size:
                older_turns = raw_history[:-window_size]
                active_history = raw_history[-window_size:]
                
                # Create structured summary of older turns
                topic_snippets = [f"- {m.get('role').capitalize()}: {m.get('content')[:80]}..." for m in older_turns]
                summary_text = f"Tóm tắt ngữ cảnh trước ({len(older_turns)} lượt):\n" + "\n".join(topic_snippets[:5])
            else:
                active_history = raw_history

        else: # full_history
            active_history = list(raw_history)

        formatted_str = memory_store.format_history_string(active_history, human_prefix=human_prefix, ai_prefix=ai_prefix)
        if summary_text:
            formatted_str = f"{summary_text}\n\n{formatted_str}"

        # Mirror variables into ExecutionContext
        context.chat_history = active_history
        context.set_variable("chat_history", active_history)
        context.set_variable("chat_history_str", formatted_str)
        context.set_variable("formatted_history", formatted_str)
        context.set_variable("session_turn_count", len(raw_history))

        context.log("info", f"Memory retrieved {len(active_history)}/{len(raw_history)} turns for session '{session_id}' [{strategy}]")

        return {
            "chat_history": active_history,
            "formatted_history": formatted_str,
            "turn_count": len(raw_history),
            "summary": summary_text
        }
