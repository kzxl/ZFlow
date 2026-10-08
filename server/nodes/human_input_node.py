"""
Human-in-the-Loop Node (Approval, Confirmation & User Feedback).
Pauses or requests confirmation from a human supervisor before executing downstream actions.
Supports Approve/Reject binary decisions, multi-option selection, and free-text inputs.
"""
from typing import Dict, Any, List, Optional
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

@NodeRegistry.register
class HumanInputNode(BaseNode):
    node_type = "human_input"
    name = "Human in the Loop"
    category = "logic"
    description = "Dừng luồng hoặc yêu cầu người dùng bấm nút Duyệt/Từ chối trước khi tiếp tục thực thi các bước quan trọng."
    icon = "UserCheck"

    inputs = [
        PortDef(name="trigger_data", data_type="any", label="Incoming Data", required=False),
        PortDef(name="prompt_text", data_type="string", label="Custom Prompt Text", required=False)
    ]
    outputs = [
        PortDef(name="approved_branch", data_type="any", label="If Approved (Duyệt)"),
        PortDef(name="rejected_branch", data_type="any", label="If Rejected (Từ chối)"),
        PortDef(name="user_choice", data_type="string", label="User Selected Choice"),
        PortDef(name="is_approved", data_type="boolean", label="Is Approved Flag")
    ]

    config_schema = {
        "approval_title": {
            "type": "string",
            "label": "Approval Dialog Title",
            "default": "Xác nhận thực thi tác vụ quan trọng"
        },
        "prompt_message": {
            "type": "textarea",
            "label": "Prompt Message for Human",
            "default": "Hệ thống đang chuẩn bị thực thi thao tác. Bạn có đồng ý phê duyệt tiếp tục không?"
        },
        "action_type": {
            "type": "select",
            "label": "Approval Mode",
            "options": ["approve_reject", "multi_choice", "text_input"],
            "default": "approve_reject"
        },
        "default_decision": {
            "type": "select",
            "label": "Default if Auto-Executed",
            "options": ["approved", "rejected"],
            "default": "approved"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        data = inputs.get("trigger_data") or inputs.get("input") or context.get_variable("input", "")
        custom_prompt = inputs.get("prompt_text") or config.get("prompt_message", "")
        title = config.get("approval_title", "Xác nhận từ người dùng")
        mode = config.get("action_type", "approve_reject")
        default_decision = config.get("default_decision", "approved")

        # Check if human response was already supplied via API or previous pause
        user_choice = (
            context.get_variable("human_choice")
            or context.get_variable("human_action")
            or context.get_variable("human_response")
            or default_decision
        )

        is_approved = str(user_choice).lower() in ("approved", "duyệt", "đồng ý", "yes", "true", "1")
        active_branch = "approved_branch" if is_approved else "rejected_branch"

        context.set_variable("human.is_approved", is_approved)
        context.set_variable("human.user_choice", user_choice)
        context.set_variable("human.active_branch", active_branch)
        context.log("info", f"Human-in-the-Loop evaluated to '{active_branch}' (User choice: '{user_choice}')")

        return {
            "active_branch": active_branch,
            "approved_branch": data if is_approved else None,
            "rejected_branch": data if not is_approved else None,
            "user_choice": user_choice,
            "is_approved": is_approved,
            "prompt_displayed": custom_prompt,
            "title": title
        }
