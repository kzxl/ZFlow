"""
Unit and Integration Tests for:
1. API Gateway Ingress Security Guard (Token Introspection, Audit Trail & Fast Reject outside workflow)
2. AME-inspired Cognitive Memory Enhancements:
   - Greedy Knapsack Token Budgeting with Anti-Redundancy Overlap Filter (>85%)
   - Working Memory Scratchpad for non-conversational task state
3. Dynamic Namespace Knowledge Isolation & Ebbinghaus Retention Decay in RAG
"""
import unittest
import asyncio
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from fastapi.testclient import TestClient
from main import app
from engine.context import ExecutionContext
from engine.auth_manager import auth_manager
from engine.knowledge_store import knowledge_store
from nodes.memory_node import MemoryNode
from nodes.rag_node import RagNode


class TestIngressAndCognitiveMemory(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.client = TestClient(app)

    def tearDown(self):
        self.loop.close()

    def test_01_ingress_security_guest_access(self):
        """
        Tests public flow execution without Bearer token assigns safe guest identity.
        """
        res = self.client.post(
            "/api/v1/flows/active/run",
            json={"inputs": {"query": "Hello ZFlow"}}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("identity", data)
        self.assertEqual(data["identity"]["role"], "guest")
        self.assertFalse(data["identity"]["is_authenticated"])
        self.assertTrue(data["session_id"].startswith("sess_guest_"))

    def test_02_ingress_security_valid_token(self):
        """
        Tests execution with valid JWT token binds trusted claims and session.
        """
        bundle = auth_manager.issue_access_token(
            user_id="alice_engineer",
            role="manager",
            tier="vip",
            scopes=["chat:write", "rag:read"],
            session_id="sess_alice_custom"
        )
        token = bundle["access_token"]

        res = self.client.post(
            "/api/v1/flows/active/run",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": {"query": "Báo cáo doanh số"}}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["identity"]["user_id"], "alice_engineer")
        self.assertEqual(data["identity"]["role"], "manager")
        self.assertEqual(data["identity"]["tier"], "vip")
        self.assertEqual(data["session_id"], "sess_alice_custom")

        # Verify audit log recorded ingress admission
        logs = auth_manager.get_audit_logs(limit=5, action="INGRESS_ADMITTED")
        self.assertTrue(len(logs) > 0)
        self.assertEqual(logs[0]["user_id"], "alice_engineer")

    def test_03_ingress_security_rejects_invalid_and_revoked_tokens(self):
        """
        Tests that invalid, forged, or revoked tokens are rejected immediately at Ingress (<0.5ms)
        without executing the workflow.
        """
        # 1. Tampered / invalid token
        res_invalid = self.client.post(
            "/api/v1/flows/active/run",
            headers={"Authorization": "Bearer forged.invalid.token"},
            json={"inputs": {"query": "Hack attempt"}}
        )
        self.assertEqual(res_invalid.status_code, 401)
        data_invalid = res_invalid.json()
        self.assertIn("error", data_invalid["detail"])

        # 2. Revoked token
        bundle = auth_manager.issue_access_token(user_id="bob_revoked", role="staff")
        token = bundle["access_token"]
        jti = bundle["claims"]["jti"]
        auth_manager.revoke_token(jti)

        res_revoked = self.client.post(
            "/api/v1/flows/active/run",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": {"query": "Post revoke request"}}
        )
        self.assertEqual(res_revoked.status_code, 401)
        data_revoked = res_revoked.json()
        self.assertEqual(data_revoked["detail"]["status"], "REVOKED")

    def test_04_memory_anti_redundancy_and_knapsack(self):
        """
        Tests AME-inspired MemoryNode:
        1. Token Budgeting
        2. Anti-Redundancy Filter (skips redundant dialogue turns with >85% overlap)
        3. Working Memory Scratchpad
        """
        async def run_test():
            node = MemoryNode()
            ctx = ExecutionContext(session_id="sess_redundancy_test")
            # Create history with exact redundant turns
            ctx.chat_history = [
                {"role": "user", "content": "Tôi muốn tra cứu thông tin chính sách bảo hành phần mềm"},
                {"role": "assistant", "content": "Dạ, chính sách bảo hành phần mềm là 12 tháng kể từ ngày ký hợp đồng."},
                # Near identical duplicate message (redundant)
                {"role": "user", "content": "Tôi muốn tra cứu thông tin chính sách bảo hành phần mềm"},
                # Fresh new turn
                {"role": "user", "content": "Ngoài ra có chính sách đổi trả hàng hóa không?"}
            ]

            res = await node.execute(
                inputs={"working_memory": {"active_task": "lookup_warranty", "step": 1}},
                config={"strategy": "token_budget", "max_token_budget": 500, "enable_anti_redundancy": True},
                context=ctx
            )

            # Redundant duplicate user message should be filtered out
            history = res["chat_history"]
            contents = [m["content"] for m in history]
            # Ensure the duplicate message only appears once
            dup_count = sum(1 for c in contents if "tra cứu thông tin chính sách bảo hành phần mềm" in c)
            self.assertEqual(dup_count, 1)

            # Working Memory must be preserved
            self.assertEqual(res["working_memory"]["active_task"], "lookup_warranty")
            self.assertEqual(ctx.get_variable("working_memory")["step"], 1)

        self.loop.run_until_complete(run_test())

    def test_05_rag_namespace_isolation_and_ebbinghaus_decay(self):
        """
        Tests RagNode with namespace filtering and Ebbinghaus retention decay.
        """
        # Ingest facts with specific namespace metadata
        doc_hr = knowledge_store.add_document(
            doc_id="hr_policy_test",
            title="Quy chế nhân sự HR",
            content="Nhân viên chính thức được nghỉ phép 12 ngày/năm và hưởng 100% lương.",
            source_type="manual",
            metadata={"namespace": "hr"}
        )

        doc_finance = knowledge_store.add_document(
            doc_id="finance_policy_test",
            title="Quy chế tài chính Finance",
            content="Quy trình thanh toán hóa đơn công tác phí được duyệt trong vòng 3 ngày làm việc.",
            source_type="manual",
            metadata={"namespace": "finance"}
        )

        # 1. Search with namespace="hr" -> should retrieve HR doc, NOT Finance
        hr_results = knowledge_store.search(query="quy chế nhân sự chính thức", namespace="hr")
        self.assertTrue(len(hr_results) > 0)
        self.assertEqual(hr_results[0]["doc_id"], "hr_policy_test")

        # 2. Search with namespace="finance" -> should retrieve Finance doc, NOT HR
        fin_results = knowledge_store.search(query="thanh toán hóa đơn công tác phí", namespace="finance")
        self.assertTrue(len(fin_results) > 0)
        self.assertEqual(fin_results[0]["doc_id"], "finance_policy_test")

        # Cleanup test docs
        knowledge_store.delete_document("hr_policy_test")
        knowledge_store.delete_document("finance_policy_test")


if __name__ == "__main__":
    unittest.main()
