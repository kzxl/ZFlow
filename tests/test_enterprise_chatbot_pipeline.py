"""
Integration and Unit Tests for Enterprise Intelligent Chatbot Pipeline:
1. Semantic Cache (Exact SHA256 & Soft Jaccard Match, Sub-millisecond latency)
2. RBAC Permission Guard (Hierarchy, role escalation & denial handling)
3. Self-Learning RAG (Role-based access filtering & dynamic fact ingestion)
4. Adaptive Context Expansion Memory (Entity pinning: Names, Phones, Emails, Orders)
5. End-to-end Workflow Execution via WorkflowRunner
"""
import asyncio
import json
import os
import sys
import unittest
import time

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server"))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from engine.context import ExecutionContext
from engine.graph import WorkflowGraph
from engine.runner import WorkflowRunner
from engine.knowledge_store import knowledge_store
from engine.memory_store import memory_store
from nodes.permission_guard_node import PermissionGuardNode
from nodes.semantic_cache_node import SemanticCacheNode, CacheStore
from nodes.memory_node import MemoryNode
from nodes.rag_node import RagNode
import nodes


class TestEnterpriseChatbotPipeline(unittest.IsolatedAsyncioTestCase):

    async def test_01_rbac_permission_guard(self):
        """Tests Role-Based Access Control logic with hierarchy and denial branches."""
        node = PermissionGuardNode()
        ctx = ExecutionContext(session_id="test_rbac_session", initial_variables={"user_role": "guest"})

        # Case 1: Guest trying to access Staff-required endpoint -> DENIED
        res_denied = await node.execute(
            inputs={"query": "Xem báo cáo chi phí công tác"},
            config={"required_role": "staff"},
            context=ctx
        )
        self.assertEqual(res_denied["active_branch"], "denied")
        self.assertFalse(res_denied["is_authorized"])
        self.assertIn("Quyền hạn không đủ", res_denied["denial_message"])
        print(f"✓ RBAC Guard Denied verified: {res_denied['reason']}")

        # Case 2: Upgrading user_role via input port to "admin" -> GRANTED
        res_granted = await node.execute(
            inputs={"query": "Xem bảng lương toàn công ty", "user_role": "admin"},
            config={"required_role": "manager"},
            context=ctx
        )
        self.assertEqual(res_granted["active_branch"], "granted")
        self.assertTrue(res_granted["is_authorized"])
        self.assertEqual(res_granted["user_role"], "admin")
        print(f"✓ RBAC Guard Granted verified: Role 'admin' >= 'manager'")

    async def test_02_semantic_cache_exact_and_fuzzy(self):
        """Tests 2-Tier Cache: Exact SHA256 and Semantic Soft Jaccard matching."""
        cache_node = SemanticCacheNode()
        ctx = ExecutionContext(session_id="test_cache_session")

        # Step 1: Write an entry to cache
        query_key = "Chính sách nghỉ phép năm của công ty như thế nào?"
        cached_answer = "Mỗi nhân viên chính thức có 12 ngày phép năm hưởng nguyên lương."

        write_res = await cache_node.execute(
            inputs={"query": query_key, "response_to_cache": cached_answer},
            config={"mode": "write_only", "ttl_seconds": 3600},
            context=ctx
        )
        self.assertEqual(write_res["cached_response"], cached_answer)

        # Step 2: Read exact match
        exact_res = await cache_node.execute(
            inputs={"query": query_key},
            config={"mode": "read_or_write", "similarity_threshold": 0.85},
            context=ctx
        )
        self.assertEqual(exact_res["active_branch"], "cache_hit")
        self.assertTrue(exact_res["is_hit"])
        self.assertEqual(exact_res["similarity_score"], 1.0)
        self.assertEqual(exact_res["cached_response"], cached_answer)
        self.assertLess(exact_res["latency_ms"], 15.0)  # Ultra-fast
        print(f"✓ Exact Cache Hit in {exact_res['latency_ms']}ms (Sim: 1.0)")

        # Step 3: Read semantic fuzzy match with high overlap
        fuzzy_query = "Chính sách nghỉ phép năm của công ty thế nào?"
        fuzzy_res = await cache_node.execute(
            inputs={"query": fuzzy_query},
            config={"mode": "read_or_write", "similarity_threshold": 0.80},
            context=ctx
        )
        self.assertEqual(fuzzy_res["active_branch"], "cache_hit")
        self.assertTrue(fuzzy_res["is_hit"])
        self.assertGreaterEqual(fuzzy_res["similarity_score"], 0.80)
        self.assertEqual(fuzzy_res["cached_response"], cached_answer)
        print(f"✓ Semantic Fuzzy Cache Hit in {fuzzy_res['latency_ms']}ms (Sim: {fuzzy_res['similarity_score']})")

        # Step 4: Cache Miss on unrelated query
        miss_res = await cache_node.execute(
            inputs={"query": "Tỷ giá USD và EUR hôm nay bao nhiêu?"},
            config={"mode": "read_or_write", "similarity_threshold": 0.85},
            context=ctx
        )
        self.assertEqual(miss_res["active_branch"], "cache_miss")
        self.assertFalse(miss_res["is_hit"])
        print("✓ Cache Miss verified on unrelated query.")

    async def test_03_self_learning_rag_with_rbac(self):
        """Tests Self-Learning RAG with role filtering and conversational fact learning."""
        rag_node = RagNode()
        ctx = ExecutionContext(session_id="test_rag_session")

        # Step 1: Seed confidential doc requiring 'admin' or 'manager'
        admin_doc_id = "doc_test_salary_confidential"
        knowledge_store.add_document(
            doc_id=admin_doc_id,
            title="Bảng lương ban giám đốc 2026",
            content="Tổng ngân sách lương điều hành là 15 tỷ VND.",
            allowed_roles=["admin", "manager"]
        )

        # Staff query should NOT find this confidential doc
        staff_res = await rag_node.execute(
            inputs={"query": "Bảng lương ban giám đốc", "user_role": "staff"},
            config={"top_k": 3, "similarity_threshold": 0.3},
            context=ctx
        )
        self.assertNotIn("15 tỷ VND", staff_res["context"])
        print("✓ RAG RBAC Verified: Staff cannot access confidential doc.")

        # Admin query CAN find this confidential doc
        admin_res = await rag_node.execute(
            inputs={"query": "Bảng lương ban giám đốc", "user_role": "admin"},
            config={"top_k": 3, "similarity_threshold": 0.3},
            context=ctx
        )
        self.assertIn("15 tỷ VND", admin_res["context"])
        print("✓ RAG RBAC Verified: Admin successfully retrieved confidential doc.")

        # Step 2: Self-learning via /learn command
        learn_query = "/learn [Chính sách tiếp khách] Chi phí tiếp khách tối đa 2.000.000đ/buổi"
        learn_res = await rag_node.execute(
            inputs={"query": learn_query, "user_role": "staff"},
            config={"auto_learn": True},
            context=ctx
        )
        self.assertEqual(learn_res["learned_status"], "success")
        print("✓ RAG Self-Learning: Ingested dynamic fact into knowledge base.")

        # Step 3: Retrieve the newly self-learned fact
        query_res = await rag_node.execute(
            inputs={"query": "Chi phí tiếp khách tối đa là bao nhiêu?", "user_role": "staff"},
            config={"top_k": 3, "similarity_threshold": 0.3},
            context=ctx
        )
        self.assertIn("2.000.000đ", query_res["context"])
        print("✓ RAG Self-Learning: Retrieved newly learned fact with freshness boost.")

    async def test_04_adaptive_memory_entity_pinning(self):
        """Tests Adaptive Context Expansion & Regex Entity Pinning in MemoryNode."""
        mem_node = MemoryNode()
        session_id = f"test_mem_{int(time.time())}"
        ctx = ExecutionContext(session_id=session_id)

        # Add message with Name, Phone, Email, and Order Code
        user_msg = "Tôi là Hoàng Nam, SĐT 0987654321, email nam.hoang@company.vn, cần tra cứu đơn hàng #ORD-8921."
        res = await mem_node.execute(
            inputs={"user_message": user_msg, "assistant_message": "Đã tiếp nhận yêu cầu của anh Nam."},
            config={"strategy": "adaptive_context_expansion", "window_size": 4, "auto_save": True},
            context=ctx
        )

        expanded = res["expanded_context"]
        pinned = res["pinned_entities"]

        self.assertIn("0987654321", expanded)
        self.assertIn("nam.hoang@company.vn", expanded)
        self.assertIn("ORD-8921", expanded)
        self.assertEqual(pinned.get("Phone"), "0987654321")
        self.assertEqual(pinned.get("Email"), "nam.hoang@company.vn")
        self.assertEqual(pinned.get("Order / Code"), "ORD-8921")
        self.assertIn("Hoàng Nam", pinned.get("User Name", ""))
        print(f"✓ Adaptive Context Expansion & Entity Pinning verified:\n{expanded[:180]}...")

    async def test_05_enterprise_pipeline_workflow_execution(self):
        """Tests execution of intelligent_enterprise_chatbot_flow.json via WorkflowRunner."""
        flow_path = os.path.join(SERVER_DIR, "storage", "intelligent_enterprise_chatbot_flow.json")
        self.assertTrue(os.path.exists(flow_path), f"File {flow_path} not found")

        with open(flow_path, "r", encoding="utf-8") as f:
            flow_def = json.load(f)

        graph = WorkflowGraph.from_dict(flow_def)

        # 1. Test System 1 Reflex shortcut: Greeting should trigger Fast Instant Reply
        runner = WorkflowRunner()
        ctx_fast = ExecutionContext(
            session_id="e2e_fast_reflex_session",
            initial_variables={"input": "Xin chào bạn!"}
        )
        res_fast = await runner.run(graph, ctx_fast)
        final_output = res_fast.get("final_output")
        self.assertIsNotNone(final_output)
        self.assertIn("ZFlow AI Assistant", str(final_output))
        print(f"✓ E2E Pipeline Fast Reflex verified in {res_fast['total_time_ms']}ms.")

        # 2. Test Deep Reasoning Path (System 1 escalate -> Cache Miss -> Permission Granted -> Memory -> RAG -> LLM -> Output)
        ctx_deep = ExecutionContext(
            session_id="e2e_deep_session",
            initial_variables={
                "input": "Tôi là Trần Tuấn, email tuan@corp.vn. Xin hãy giải thích quy định bảo mật thông tin nội bộ.",
                "user_role": "staff"
            }
        )
        res_deep = await runner.run(graph, ctx_deep)
        final_output_deep = res_deep.get("final_output")
        self.assertIsNotNone(final_output_deep)
        print(f"✓ E2E Pipeline Deep Path verified in {res_deep['total_time_ms']}ms -> output received.")


if __name__ == "__main__":
    unittest.main()
