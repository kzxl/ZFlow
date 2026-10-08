"""
Unit and Integration Tests for ZFlow Authentication, JWT Access Tokens, and Session Isolation:
1. RFC 7519 Compliant JWT Token Issuance & Verification (HS256)
2. Signature Tampering and Expiration Checks
3. Token Revocation & Blacklist Enforcement
4. AuthNode Login & Session Token Issuance
5. AuthNode Token Verification & Automatic Claims Binding (Role, Tier, Session ID)
6. Multi-Session Context Isolation with Downstream RBAC Permission Guard
"""
import unittest
import asyncio
import os
import sys
import time
from typing import Dict, Any

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from engine.context import ExecutionContext
from engine.graph import WorkflowGraph
from engine.runner import WorkflowRunner
from engine.auth_manager import auth_manager, AuthManager
from nodes.auth_node import AuthNode
from nodes.permission_guard_node import PermissionGuardNode
from nodes.output_node import OutputNode
from nodes.input_node import InputNode
from nodes.webhook_node import WebhookTriggerNode
from fastapi.testclient import TestClient
from main import app


class TestAuthAndSessionTokens(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_01_jwt_issuance_and_verification(self):
        """
        Tests standard RFC 7519 HS256 JWT creation, structure, and valid verification.
        """
        manager = AuthManager(secret_key="unit_test_secret_key_123")
        bundle = manager.issue_access_token(
            user_id="alice_engineer",
            role="manager",
            tier="vip",
            scopes=["rag:read", "code:exec"],
            session_id="sess_alice_42",
            expires_in_seconds=300
        )

        token = bundle["access_token"]
        self.assertTrue(isinstance(token, str))
        self.assertEqual(len(token.split(".")), 3)

        # Verify valid token
        is_valid, claims, reason = manager.verify_token(token)
        self.assertTrue(is_valid)
        self.assertEqual(claims["sub"], "alice_engineer")
        self.assertEqual(claims["role"], "manager")
        self.assertEqual(claims["tier"], "vip")
        self.assertEqual(claims["session_id"], "sess_alice_42")
        self.assertIn("code:exec", claims["scopes"])

    def test_02_tampered_signature_and_expiration(self):
        """
        Tests that tampered tokens or expired tokens are strictly rejected.
        """
        manager = AuthManager(secret_key="unit_test_secret_key_123")
        bundle = manager.issue_access_token("bob", expires_in_seconds=1)
        token = bundle["access_token"]

        # 1. Tamper with signature
        tampered = token[:-4] + "xxxx"
        is_valid, claims, reason = manager.verify_token(tampered)
        self.assertFalse(is_valid)
        self.assertIn("Invalid JWT signature", reason)

        # 2. Test expiration
        time.sleep(1.2)
        is_valid, claims, reason = manager.verify_token(token)
        self.assertFalse(is_valid)
        self.assertIn("expired", reason.lower())

    def test_03_token_revocation_blacklist(self):
        """
        Tests that revoked tokens cannot be verified even if signature is valid.
        """
        manager = AuthManager()
        bundle = manager.issue_access_token("charlie", expires_in_seconds=600)
        token = bundle["access_token"]
        jti = bundle["claims"]["jti"]

        # Initially valid
        is_valid, _, _ = manager.verify_token(token)
        self.assertTrue(is_valid)

        # Revoke token
        manager.revoke_token(jti, session_id=bundle["session_id"])
        is_valid_after, _, reason = manager.verify_token(token)
        self.assertFalse(is_valid_after)
        self.assertIn("revoked", reason.lower())

    def test_04_auth_node_login_action(self):
        """
        Tests AuthNode in 'login_issue_token' mode for credential verification and token generation.
        """
        async def run_test():
            node = AuthNode()
            ctx = ExecutionContext(session_id="login_test_sess")

            # 1. Invalid credentials -> 401 Unauthorized
            res_fail = await node.execute(
                inputs={"credentials": {"username": "admin", "password": "wrong_password"}},
                config={"action": "login_issue_token"},
                context=ctx
            )
            self.assertEqual(res_fail["active_branch"], "unauthorized")
            self.assertEqual(res_fail["unauthorized"]["status"], 401)

            # 2. Valid credentials -> 200 Authenticated + Token Issued
            res_success = await node.execute(
                inputs={"credentials": {"username": "admin", "password": "admin123"}},
                config={"action": "login_issue_token", "bind_session_to_context": True},
                context=ctx
            )
            self.assertEqual(res_success["active_branch"], "authenticated")
            self.assertTrue(len(res_success["access_token"]) > 20)
            self.assertEqual(res_success["user_claims"]["role"], "admin")
            self.assertEqual(res_success["user_claims"]["tier"], "vip")
            # Context must have claims bound
            self.assertEqual(ctx.get_variable("user_role"), "admin")
            self.assertEqual(ctx.get_variable("user_tier"), "vip")

        self.loop.run_until_complete(run_test())

    def test_05_auth_guard_piped_to_permission_guard(self):
        """
        Tests end-to-end integration:
        AuthNode verifies Bearer Token -> injects role -> PermissionGuard checks role without manual input.
        """
        async def run_test():
            # 1. Issue token for staff user
            bundle = auth_manager.issue_access_token(
                user_id="david",
                role="staff",
                tier="standard",
                session_id="david_sess_101"
            )
            staff_token = bundle["access_token"]

            # 2. Build DAG: AuthNode (Token Guard) -> PermissionGuard (Requires manager) -> Output
            flow_def = {
                "nodes": [
                    {
                        "id": "auth_guard",
                        "type": "auth",
                        "title": "JWT Guard",
                        "config": {"action": "verify_bearer_token"}
                    },
                    {
                        "id": "perm_guard",
                        "type": "permission_guard",
                        "title": "Manager RBAC Guard",
                        "config": {"required_role": "manager"}
                    },
                    {
                        "id": "out_granted",
                        "type": "output",
                        "title": "Granted",
                        "config": {"output_key": "reply", "prefix": "SUCCESS: "}
                    },
                    {
                        "id": "out_denied",
                        "type": "output",
                        "title": "Denied",
                        "config": {"output_key": "reply", "prefix": "DENIED: "}
                    }
                ],
                "edges": [
                    {"id": "e1", "source": "auth_guard", "target": "perm_guard", "sourceHandle": "authenticated", "targetHandle": "query"},
                    {"id": "e2", "source": "perm_guard", "target": "out_granted", "sourceHandle": "granted", "targetHandle": "input"},
                    {"id": "e3", "source": "perm_guard", "target": "out_denied", "sourceHandle": "denied", "targetHandle": "input"}
                ]
            }

            graph = WorkflowGraph.from_dict(flow_def)

            # Test A: Staff token -> Auth succeeds, but Permission Guard denies (staff < manager)
            runner = WorkflowRunner()
            ctx_staff = ExecutionContext(
                session_id="test_staff_pipe",
                initial_variables={"input": "Xem báo cáo doanh thu tài chính"}
            )
            ctx_staff.set_variable("webhook_headers", {"authorization": f"Bearer {staff_token}"})
            
            res_staff = await runner.run(graph, ctx_staff)
            self.assertIn("DENIED", str(res_staff["final_output"]))
            self.assertEqual(ctx_staff.session_id, "david_sess_101")  # Session ID bound from token!

            # Test B: Issue token for admin user -> Both Auth & Permission succeed
            admin_bundle = auth_manager.issue_access_token(
                user_id="emily",
                role="admin",
                tier="vip",
                session_id="emily_sess_202"
            )
            ctx_admin = ExecutionContext(
                session_id="test_admin_pipe",
                initial_variables={"input": "Xem báo cáo doanh thu tài chính"}
            )
            ctx_admin.set_variable("webhook_headers", {"authorization": f"Bearer {admin_bundle['access_token']}"})

            res_admin = await runner.run(graph, ctx_admin)
            self.assertIn("SUCCESS", str(res_admin["final_output"]))
            self.assertEqual(ctx_admin.session_id, "emily_sess_202")  # Bound cleanly to Emily's session!

        self.loop.run_until_complete(run_test())

    def test_06_input_node_and_webhook_node_token_forwarding(self):
        """
        Tests that both InputNode and WebhookTriggerNode extract and forward access_token cleanly.
        """
        async def run_test():
            bundle = auth_manager.issue_access_token(user_id="test_user", role="staff")
            token = bundle["access_token"]

            # 1. Test InputNode with access_token in variables
            input_node = InputNode()
            ctx_input = ExecutionContext(session_id="input_sess_1", initial_variables={"input": "Xin chao", "access_token": token})
            res_input = await input_node.execute({}, {}, ctx_input)
            self.assertEqual(res_input["access_token"], token)
            self.assertEqual(res_input["query"], "Xin chao")
            self.assertEqual(ctx_input.get_variable("access_token"), token)

            # 2. Test InputNode with Bearer header
            ctx_input2 = ExecutionContext(session_id="input_sess_2", initial_variables={"input": "Xin chao 2"})
            ctx_input2.set_variable("webhook_headers", {"authorization": f"Bearer {token}"})
            res_input2 = await input_node.execute({}, {}, ctx_input2)
            self.assertEqual(res_input2["access_token"], token)

            # 3. Test WebhookTriggerNode with Bearer header
            webhook_node = WebhookTriggerNode()
            ctx_webhook = ExecutionContext(session_id="wh_sess_1")
            ctx_webhook.set_variable("webhook_payload", {"message": "webhook message", "event": "chat_event"})
            ctx_webhook.set_variable("webhook_headers", {"authorization": f"Bearer {token}"})
            res_wh = await webhook_node.execute({}, {}, ctx_webhook)
            self.assertEqual(res_wh["access_token"], token)
            self.assertEqual(res_wh["query"], "webhook message")
            self.assertEqual(res_wh["event"], "chat_event")
            self.assertEqual(ctx_webhook.get_variable("access_token"), token)

            # 4. Test WebhookTriggerNode with token inside payload
            ctx_webhook2 = ExecutionContext(session_id="wh_sess_2")
            ctx_webhook2.set_variable("webhook_payload", {"action": "do_task", "access_token": token})
            ctx_webhook2.set_variable("webhook_headers", {})
            res_wh2 = await webhook_node.execute({}, {}, ctx_webhook2)
            self.assertEqual(res_wh2["access_token"], token)
            self.assertEqual(res_wh2["query"], "do_task")

        self.loop.run_until_complete(run_test())

    def test_07_token_introspection_and_audit_logging(self):
        """
        Tests OAuth 2.0 RFC 7662 token introspection and immutable audit logging.
        """
        manager = AuthManager()
        bundle = manager.issue_access_token(
            user_id="audit_tester",
            role="manager",
            tier="vip",
            scopes=["chat:write", "analytics:read"],
            expires_in_seconds=600
        )
        token = bundle["access_token"]
        jti = bundle["claims"]["jti"]

        # 1. Introspect valid active token
        intro_valid = manager.introspect_token(token, ip_address="192.168.1.100", endpoint="/api/v1/auth/introspect")
        self.assertTrue(intro_valid["active"])
        self.assertEqual(intro_valid["sub"], "audit_tester")
        self.assertEqual(intro_valid["role"], "manager")
        self.assertEqual(intro_valid["tier"], "vip")
        self.assertIn("chat:write", intro_valid["scopes"])
        self.assertEqual(intro_valid["audit"]["validation"], "PASSED")

        # 2. Check audit logs contain the introspection event
        logs = manager.get_audit_logs(limit=10, action="INTROSPECT")
        self.assertTrue(len(logs) > 0)
        latest = logs[0]
        self.assertEqual(latest["action"], "INTROSPECT")
        self.assertEqual(latest["status"], "SUCCESS")
        self.assertEqual(latest["user_id"], "audit_tester")
        self.assertEqual(latest["ip_address"], "192.168.1.100")

        # 3. Revoke and introspect again
        manager.revoke_token(jti)
        intro_revoked = manager.introspect_token(token, ip_address="192.168.1.100")
        self.assertFalse(intro_revoked["active"])
        self.assertEqual(intro_revoked["audit"]["validation"], "REJECTED")
        self.assertEqual(intro_revoked["status"], "REVOKED")

    def test_08_auth_api_endpoints(self):
        """
        Tests FastAPI REST endpoints:
        - POST /api/v1/auth/login
        - POST /api/v1/auth/introspect
        - GET /api/v1/auth/audit-logs
        - POST /api/v1/auth/revoke
        - GET /api/v1/auth/users
        """
        client = TestClient(app)

        # 1. Login with demo admin
        login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.json()
        self.assertIn("access_token", login_data)
        token = login_data["access_token"]
        self.assertEqual(login_data["user"]["role"], "admin")

        # 2. Introspect via endpoint
        intro_res = client.post("/api/v1/auth/introspect", json={"token": token})
        self.assertEqual(intro_res.status_code, 200)
        intro_data = intro_res.json()
        self.assertTrue(intro_data["active"])
        self.assertEqual(intro_data["sub"], "admin")
        self.assertEqual(intro_data["role"], "admin")
        self.assertEqual(intro_data["audit"]["validation"], "PASSED")

        # 3. Tra cứu audit logs
        logs_res = client.get("/api/v1/auth/audit-logs?limit=5")
        self.assertEqual(logs_res.status_code, 200)
        logs_data = logs_res.json()
        self.assertEqual(logs_data["status"], "success")
        self.assertTrue(len(logs_data["logs"]) > 0)

        # 4. Revoke token
        revoke_res = client.post("/api/v1/auth/revoke", json={"token": token})
        self.assertEqual(revoke_res.status_code, 200)
        revoke_data = revoke_res.json()
        self.assertEqual(revoke_data["status"], "success")

        # 5. Introspect revoked token -> active must be False
        intro_revoked_res = client.post("/api/v1/auth/introspect", json={"token": token})
        self.assertEqual(intro_revoked_res.status_code, 200)
        intro_revoked_data = intro_revoked_res.json()
        self.assertFalse(intro_revoked_data["active"])
        self.assertEqual(intro_revoked_data["audit"]["validation"], "REJECTED")
        self.assertEqual(intro_revoked_data["status"], "REVOKED")

        # 6. List users
        users_res = client.get("/api/v1/auth/users")
        self.assertEqual(users_res.status_code, 200)
        users_data = users_res.json()
        self.assertTrue(len(users_data["users"]) >= 3)


if __name__ == "__main__":
    unittest.main()
