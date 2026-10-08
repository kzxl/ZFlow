"""
Auth & Session Token Node for ZFlow.
Handles user authentication, RFC 7519 JWT access token issuance, token verification,
and automatic context session binding (user_role, user_tier, user_scopes, session_id).
"""
from typing import Dict, Any, AsyncGenerator, Optional
import json
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext
from engine.auth_manager import auth_manager

@NodeRegistry.register
class AuthNode(BaseNode):
    node_type = "auth"
    name = "Auth & Session Guard"
    category = "logic"
    description = "Xác thực danh tính, cấp phát Access Token (JWT), quản lý phiên (Session ID) và trích xuất claims (role, tier, scopes) nạp vào ExecutionContext."
    icon = "Key"

    inputs = [
        PortDef(name="input", data_type="any", label="Payload / Query", required=False),
        PortDef(name="credentials", data_type="object", label="Credentials / Token", required=False),
        PortDef(name="headers", data_type="object", label="HTTP Headers (Opt)", required=False)
    ]

    outputs = [
        PortDef(name="authenticated", data_type="any", label="✅ Authenticated Path"),
        PortDef(name="unauthorized", data_type="object", label="⛔ 401 Unauthorized Path"),
        PortDef(name="access_token", data_type="string", label="JWT Access Token"),
        PortDef(name="session_id", data_type="string", label="Session ID"),
        PortDef(name="user_claims", data_type="object", label="User Claims (Role/Tier)"),
        PortDef(name="active_branch", data_type="string", label="Active Branch Handle")
    ]

    config_schema = {
        "action": {
            "type": "select",
            "label": "Authentication Action",
            "options": [
                "verify_bearer_token",
                "login_issue_token",
                "mock_session_bind"
            ],
            "default": "verify_bearer_token"
        },
        "default_username": {
            "type": "string",
            "label": "Default Username (if not in input)",
            "default": "staff"
        },
        "default_password": {
            "type": "password",
            "label": "Default Password (if not in input)",
            "default": "staff123"
        },
        "token_expiry_seconds": {
            "type": "number",
            "label": "Access Token Expiry (Seconds)",
            "min": 60,
            "max": 604800,
            "default": 3600
        },
        "bind_session_to_context": {
            "type": "boolean",
            "label": "Bind Token Session ID to Workflow Context",
            "default": True
        },
        "unauthorized_message": {
            "type": "string",
            "label": "Unauthorized Error Message",
            "default": "⛔ 401 Unauthorized: Access token không hợp lệ, đã bị thu hồi hoặc phiên đăng nhập đã hết hạn."
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Executes identity verification, token issuance, or claims binding.
        """
        action = config.get("action", "verify_bearer_token")
        query_input = inputs.get("input")
        if query_input is None:
            query_input = context.get_variable("input") or context.get_variable("query", "")

        headers = inputs.get("headers") or context.get_variable("webhook_headers") or {}
        bind_session = config.get("bind_session_to_context", True)
        unauth_msg = config.get("unauthorized_message", "⛔ 401 Unauthorized")

        # -------------------------------------------------------------
        # Action 1: Login & Issue JWT Access Token
        # -------------------------------------------------------------
        if action == "login_issue_token":
            creds = inputs.get("credentials") or {}
            username = ""
            password = ""
            if isinstance(creds, dict):
                username = creds.get("username") or creds.get("user") or ""
                password = creds.get("password") or creds.get("pass") or ""
            elif isinstance(creds, str) and ":" in creds:
                parts = creds.split(":", 1)
                username, password = parts[0], parts[1]

            if not username:
                username = config.get("default_username", "staff")
            if not password:
                password = config.get("default_password", "staff123")

            user_record = auth_manager.authenticate_user(username, password)
            if not user_record:
                context.log("error", f"Login failed for username '{username}'.")
                context.set_variable("final_output", unauth_msg)
                return {
                    "authenticated": None,
                    "unauthorized": {"status": 401, "error": "Invalid credentials", "message": unauth_msg},
                    "access_token": "",
                    "session_id": context.session_id,
                    "user_claims": {},
                    "active_branch": "unauthorized"
                }

            # Issue JWT token
            expiry = int(config.get("token_expiry_seconds", 3600))
            sess_id = f"user_{username}_{context.session_id[:8]}" if not context.session_id.startswith("user_") else context.session_id
            token_bundle = auth_manager.issue_access_token(
                user_id=username,
                role=user_record["role"],
                tier=user_record["tier"],
                scopes=user_record["scopes"],
                session_id=sess_id,
                expires_in_seconds=expiry
            )

            if bind_session:
                context.session_id = sess_id
                context.set_variable("session_id", sess_id)

            # Inject claims into context
            context.set_variable("user_id", username)
            context.set_variable("user_role", user_record["role"])
            context.set_variable("user_tier", user_record["tier"])
            context.set_variable("user_scopes", user_record["scopes"])
            context.set_variable("access_token", token_bundle["access_token"])

            context.log("info", f"User '{username}' authenticated successfully. Issued token (Role: {user_record['role']}, Tier: {user_record['tier']}).")

            return {
                "authenticated": query_input,
                "unauthorized": None,
                "access_token": token_bundle["access_token"],
                "session_id": sess_id,
                "user_claims": token_bundle["claims"],
                "active_branch": "authenticated"
            }

        # -------------------------------------------------------------
        # Action 2: Verify Bearer Token (Token Guard)
        # -------------------------------------------------------------
        elif action == "verify_bearer_token":
            # Extract token from headers, credentials, or context variables
            token_str = ""
            if isinstance(headers, dict):
                token_str = headers.get("authorization") or headers.get("Authorization") or ""
            if not token_str and isinstance(inputs.get("credentials"), str):
                token_str = inputs.get("credentials")
            elif not token_str and isinstance(inputs.get("credentials"), dict):
                token_str = inputs.get("credentials", {}).get("token") or inputs.get("credentials", {}).get("access_token") or ""
            if not token_str:
                token_str = context.get_variable("access_token") or context.get_variable("token") or ""

            is_valid, claims, reason = auth_manager.verify_token(token_str)
            if not is_valid:
                context.log("warning", f"Token verification failed: {reason}")
                context.set_variable("final_output", unauth_msg)
                return {
                    "authenticated": None,
                    "unauthorized": {"status": 401, "error": reason, "message": unauth_msg},
                    "access_token": token_str,
                    "session_id": context.session_id,
                    "user_claims": {},
                    "active_branch": "unauthorized"
                }

            # Valid token -> bind session and claims
            claims_dict = claims or {}
            sess_id = claims_dict.get("session_id") or context.session_id
            if bind_session and sess_id:
                context.session_id = sess_id
                context.set_variable("session_id", sess_id)

            user_role = claims_dict.get("role", "guest")
            user_tier = claims_dict.get("tier", "free")
            user_scopes = claims_dict.get("scopes", [])
            user_id = claims_dict.get("sub", "unknown")

            context.set_variable("user_id", user_id)
            context.set_variable("user_role", user_role)
            context.set_variable("user_tier", user_tier)
            context.set_variable("user_scopes", user_scopes)
            context.set_variable("access_token", token_str)

            context.log("info", f"Verified token for user '{user_id}' (Role: '{user_role}', Tier: '{user_tier}', Session: '{sess_id}').")

            return {
                "authenticated": query_input,
                "unauthorized": None,
                "access_token": token_str,
                "session_id": sess_id,
                "user_claims": claims_dict,
                "active_branch": "authenticated"
            }

        # -------------------------------------------------------------
        # Action 3: Mock / Quick Session Bind (For local testing)
        # -------------------------------------------------------------
        else:
            uname = config.get("default_username", "staff")
            role = "staff"
            tier = "standard"
            sess_id = f"mock_{uname}_{context.session_id[:8]}"

            context.session_id = sess_id
            context.set_variable("session_id", sess_id)
            context.set_variable("user_id", uname)
            context.set_variable("user_role", role)
            context.set_variable("user_tier", tier)

            token_bundle = auth_manager.issue_access_token(uname, role=role, tier=tier, session_id=sess_id)
            context.set_variable("access_token", token_bundle["access_token"])

            return {
                "authenticated": query_input,
                "unauthorized": None,
                "access_token": token_bundle["access_token"],
                "session_id": sess_id,
                "user_claims": token_bundle["claims"],
                "active_branch": "authenticated"
            }

    async def execute_stream(
        self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        res = await self.execute(inputs, config, context)
        yield {"type": "result", "data": res}
