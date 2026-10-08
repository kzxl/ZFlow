"""
ZFlow Execution Context and State Management.
Stores conversation state, session memory, node execution logs, and runtime variables.
"""
from typing import Any, Dict, List, Optional
import time
import re

class ExecutionContext:
    def __init__(self, session_id: str = "default_session", initial_variables: Optional[Dict[str, Any]] = None):
        self.session_id: str = session_id
        self.variables: Dict[str, Any] = initial_variables.copy() if initial_variables else {}
        self.chat_history: List[Dict[str, str]] = []
        self.node_outputs: Dict[str, Dict[str, Any]] = {}
        self.node_states: Dict[str, str] = {} # idle, running, completed, error
        self.logs: List[Dict[str, Any]] = []
        self.loop_counters: Dict[str, int] = {}
        self.start_time: float = time.time()
        self.is_aborted: bool = False

    def set_variable(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def record_node_output(self, node_id: str, output: Dict[str, Any]) -> None:
        self.node_outputs[node_id] = output
        # Also mirror flat outputs into variables with node_id prefix: {node_id.output_key}
        for k, v in output.items():
            self.variables[f"{node_id}.{k}"] = v
            # If top-level variable doesn't exist, provide convenient fallback
            if k not in self.variables:
                self.variables[k] = v

    def get_node_output(self, node_id: str, port_name: Optional[str] = None) -> Any:
        outputs = self.node_outputs.get(node_id, {})
        if port_name is not None:
            return outputs.get(port_name)
        return outputs

    def append_chat(self, role: str, content: str) -> None:
        self.chat_history.append({"role": role, "content": content})

    def log(self, level: str, message: str, node_id: Optional[str] = None, data: Optional[Any] = None) -> None:
        self.logs.append({
            "timestamp": time.time(),
            "level": level,
            "node_id": node_id,
            "message": message,
            "data": data
        })

    def interpolate(self, text: str) -> str:
        """
        Interpolates {variable_name} or {node_id.output_key} in a template string.
        Gracefully keeps {variable_name} if key is not found.
        """
        if not text or not isinstance(text, str):
            return ""

        def replace_match(match):
            key = match.group(1).strip()
            if key in self.variables:
                val = self.variables[key]
                return str(val) if val is not None else ""
            return match.group(0)

        return re.sub(r"\{([a-zA-Z0-9_.-]+)\}", replace_match, text)

    def increment_loop(self, node_id: str) -> int:
        count = self.loop_counters.get(node_id, 0) + 1
        self.loop_counters[node_id] = count
        return count
