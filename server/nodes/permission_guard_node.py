"""
RBAC Permission Guard Node.
Enforces Role-Based Access Control and Entitlement checks on user queries or workflows.
Gates sensitive data access, code execution, financial records, and operational tools.
"""
from typing import Dict, Any, List, Optional
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

ROLE_HIERARCHY = {
    "guest": 1,
    "staff": 2,
    "manager": 3,
    "admin": 4
}


@NodeRegistry.register
class PermissionGuardNode(BaseNode):
    node_type = "permission_guard"
    name = "RBAC Permission Guard"
    category = "logic"
    description = "Kiểm tra phân quyền người dùng (Admin, Manager, Staff, Guest) trước khi truy cập tài liệu nhạy cảm hoặc thực thi công cụ nguy hiểm."
    icon = "UserCheck"

    inputs = [
        PortDef(name="query", data_type="string", label="Incoming Query / Action", required=True),
        PortDef(name="user_role", data_type="string", label="User Role (Optional)", required=False)
    ]
    outputs = [
        PortDef(name="granted", data_type="string", label="✅ Granted (Authorized)"),
        PortDef(name="denied", data_type="string", label="⛔ Denied (Unauthorized)"),
        PortDef(name="active_branch", data_type="string", label="Active Branch"),
        PortDef(name="is_authorized", data_type="boolean", label="Is Authorized"),
        PortDef(name="user_role", data_type="string", label="Resolved User Role"),
        PortDef(name="reason", data_type="string", label="Evaluation Reason"),
        PortDef(name="denial_message", data_type="string", label="Denial Response Text")
    ]

    config_schema = {
        "required_role": {
            "type": "select",
            "label": "Minimum Required Role",
            "options": ["guest", "staff", "manager", "admin"],
            "default": "staff"
        },
        "required_scope": {
            "type": "string",
            "label": "Specific Scope / Permission Key (e.g. finance:read, salary:view)",
            "default": ""
        },
        "denial_response_template": {
            "type": "string",
            "label": "Denial Message Template",
            "default": "⛔ Bạn không có quyền truy cập chức năng hoặc tài liệu này. (Yêu cầu vai trò tối thiểu: {required_role}, Vai trò hiện tại của bạn: {user_role})."
        },
        "role_context_variable": {
            "type": "string",
            "label": "Context Variable Name for User Role",
            "default": "user_role"
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        query = str(
            inputs.get("query")
            or inputs.get("input")
            or context.get_variable("query")
            or context.get_variable("input", "")
        ).strip()

        role_var_name = config.get("role_context_variable", "user_role")
        user_role_raw = str(
            inputs.get("user_role")
            or context.get_variable(role_var_name)
            or context.get_variable("role")
            or "guest"
        ).strip().lower()

        required_role = config.get("required_role", "staff").lower()
        required_scope = config.get("required_scope", "").strip()
        denial_tpl = config.get("denial_response_template", "⛔ Quyền hạn không đủ.")

        user_level = ROLE_HIERARCHY.get(user_role_raw, 1)
        req_level = ROLE_HIERARCHY.get(required_role, 2)

        is_authorized = True
        reason = f"User role '{user_role_raw}' meets required level for '{required_role}'."

        # 1. Level check
        if user_level < req_level:
            is_authorized = False
            reason = f"User level {user_level} ({user_role_raw}) is below required level {req_level} ({required_role})."

        # 2. Scope check (if defined)
        user_scopes = context.get_variable("user_scopes") or []
        if is_authorized and required_scope:
            if isinstance(user_scopes, str):
                user_scopes = [s.strip() for s in user_scopes.split(",")]
            if required_scope not in user_scopes and user_role_raw != "admin":
                is_authorized = False
                reason = f"Missing required scope '{required_scope}'."

        active_branch = "granted" if is_authorized else "denied"
        denial_msg = denial_tpl.format(
            required_role=required_role,
            user_role=user_role_raw,
            query=query
        )

        context.set_variable("is_authorized", is_authorized)
        context.set_variable("user_role", user_role_raw)
        context.set_variable("permission_active_branch", active_branch)

        if not is_authorized:
            context.set_variable("denial_message", denial_msg)
            context.set_variable("final_output", denial_msg)
            context.log("warn", f"Permission denied for user role '{user_role_raw}' (Required: '{required_role}').")
        else:
            context.log("info", f"Permission granted for user role '{user_role_raw}'.")

        return {
            "active_branch": active_branch,
            "is_authorized": is_authorized,
            "granted": query if is_authorized else "",
            "denied": denial_msg if not is_authorized else "",
            "user_role": user_role_raw,
            "reason": reason,
            "denial_message": denial_msg if not is_authorized else ""
        }
