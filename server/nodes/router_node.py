"""
Router Node for Multi-Branch Conditional Routing in Chatbot Workflows.
Supports both classic If/Else evaluation and Switch-Case multi-route branching.
Evaluates input variables and activates the matching branch route.
"""
from typing import Dict, Any, List, Optional
import re
import json
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

def evaluate_condition(text: str, operator: str, value: str) -> bool:
    """
    Evaluates a single condition rule against target text.
    """
    if not value and operator != "is_empty":
        return False

    op = (operator or "contains").lower().strip()
    val = str(value)
    clean_text = text.strip()

    if op == "contains":
        keywords = [k.strip() for k in val.split("|") if k.strip()]
        return any(k.lower() in clean_text.lower() for k in keywords)

    elif op == "not_contains":
        keywords = [k.strip() for k in val.split("|") if k.strip()]
        return not any(k.lower() in clean_text.lower() for k in keywords)

    elif op == "equals":
        return clean_text.lower() == val.strip().lower()

    elif op == "not_equals":
        return clean_text.lower() != val.strip().lower()

    elif op == "starts_with":
        prefixes = [p.strip() for p in val.split("|") if p.strip()]
        return any(clean_text.lower().startswith(p.lower()) for p in prefixes)

    elif op == "ends_with":
        suffixes = [s.strip() for s in val.split("|") if s.strip()]
        return any(clean_text.lower().endswith(s.lower()) for s in suffixes)

    elif op == "regex":
        try:
            return bool(re.search(val, clean_text, re.IGNORECASE))
        except Exception:
            return False

    elif op == "is_empty":
        return len(clean_text) == 0

    return False


@NodeRegistry.register
class RouterNode(BaseNode):
    node_type = "router"
    name = "Condition Router"
    category = "logic"
    description = "Branches the workflow dynamically using If/Else rules or multi-case Switch/Case routing."
    icon = "GitBranch"

    inputs = [
        PortDef(name="input_text", data_type="string", label="Input Text", required=True)
    ]
    outputs = [
        PortDef(name="true_branch", data_type="string", label="If True (Match)"),
        PortDef(name="false_branch", data_type="string", label="If False (Default)"),
        PortDef(name="active_branch", data_type="string", label="Active Branch ID"),
        PortDef(name="matched_rule", data_type="string", label="Matched Rule")
    ]

    config_schema = {
        "mode": {
            "type": "select",
            "label": "Routing Mode",
            "options": ["switch_case", "if_else"],
            "default": "switch_case"
        },
        "rule_type": {
            "type": "select",
            "label": "If-Else Evaluation Rule",
            "options": ["contains", "regex", "starts_with", "equals"],
            "default": "contains"
        },
        "target_pattern": {
            "type": "string",
            "label": "If-Else Keyword / Pattern",
            "default": "giúp|hỗ trợ|support|help"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        text = str(
            inputs.get("input_text")
            or inputs.get("input")
            or context.get_variable("prompt")
            or context.get_variable("user_query")
            or context.get_variable("input", "")
        )
        mode = config.get("mode", "switch_case")

        # Resolve branches for switch_case mode
        raw_branches = config.get("branches")
        branches: List[Dict[str, Any]] = []

        if isinstance(raw_branches, str):
            try:
                branches = json.loads(raw_branches)
            except Exception:
                branches = []
        elif isinstance(raw_branches, list):
            branches = raw_branches

        active_branch = "default_branch"
        matched_rule = "default"
        is_matched = False

        if mode == "switch_case" and branches:
            # Multi-branch switch case evaluation
            for b in branches:
                b_id = b.get("id") or b.get("name") or "branch"
                op = b.get("operator", "contains")
                val = b.get("value", "")

                if evaluate_condition(text, op, val):
                    active_branch = b_id
                    matched_rule = f"{b.get('name', b_id)} [{op}: {val}]"
                    is_matched = True
                    break

            if not is_matched:
                active_branch = "default_branch"
                matched_rule = "Default / Else"

        else:
            # Simple If / Else evaluation
            rule_type = config.get("rule_type", "contains")
            pattern = config.get("target_pattern", "")
            is_matched = evaluate_condition(text, rule_type, pattern)

            active_branch = "true_branch" if is_matched else "false_branch"
            matched_rule = f"{rule_type}:{pattern}" if is_matched else "default_false"

        context.set_variable("router.active_branch", active_branch)
        context.set_variable("router.matched_rule", matched_rule)
        context.set_variable("router.is_matched", is_matched)
        context.log("info", f"Router [{mode}] evaluated to '{active_branch}' via rule: '{matched_rule}'")

        # Prepare outputs with active branch having the text payload
        result: Dict[str, Any] = {
            "active_branch": active_branch,
            "matched_rule": matched_rule,
            "is_matched": is_matched,
            "input_text": text,
            "default_branch": text if active_branch == "default_branch" else None,
            "true_branch": text if (active_branch == "true_branch" or (is_matched and mode == "switch_case")) else None,
            "false_branch": text if (active_branch in ("false_branch", "default_branch")) else None
        }

        # Set specific branch keys so connected edges receive data
        for b in branches:
            b_id = b.get("id")
            if b_id:
                result[b_id] = text if active_branch == b_id else None

        result[active_branch] = text
        return result
