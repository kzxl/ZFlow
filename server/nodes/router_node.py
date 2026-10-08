"""
Router Node for Conditional Branching in Chatbot Workflows.
Evaluates input variables and activates true_branch or false_branch.
"""
from typing import Dict, Any
import re
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class RouterNode(BaseNode):
    node_type = "router"
    name = "Condition Router"
    category = "logic"
    description = "Branches the workflow based on keywords, regex, or value conditions."
    icon = "GitBranch"

    inputs = [
        PortDef(name="input_text", data_type="string", label="Input Text", required=True)
    ]
    outputs = [
        PortDef(name="true_branch", data_type="string", label="If True (Match)"),
        PortDef(name="false_branch", data_type="string", label="If False (Default)"),
        PortDef(name="matched_rule", data_type="string", label="Matched Rule")
    ]

    config_schema = {
        "rule_type": {
            "type": "select",
            "label": "Evaluation Rule",
            "options": ["contains", "regex", "starts_with"],
            "default": "contains"
        },
        "target_pattern": {
            "type": "string",
            "label": "Keyword / Pattern",
            "default": "giúp|hỗ trợ|support|help"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        text = str(inputs.get("input_text") or context.get_variable("user_query", ""))
        rule_type = config.get("rule_type", "contains")
        pattern = config.get("target_pattern", "")

        is_match = False
        if rule_type == "contains":
            keywords = [k.strip() for k in pattern.split("|") if k.strip()]
            is_match = any(k.lower() in text.lower() for k in keywords)
        elif rule_type == "starts_with":
            prefixes = [k.strip() for k in pattern.split("|") if k.strip()]
            is_match = any(text.lower().startswith(p.lower()) for p in prefixes)
        elif rule_type == "regex":
            try:
                is_match = bool(re.search(pattern, text, re.IGNORECASE))
            except Exception:
                is_match = False

        context.set_variable("router_result", is_match)
        context.log("info", f"Router evaluated '{pattern}' against text -> {is_match}")

        return {
            "true_branch": text if is_match else None,
            "false_branch": text if not is_match else None,
            "is_matched": is_match,
            "matched_rule": f"{rule_type}:{pattern}" if is_match else "none"
        }
