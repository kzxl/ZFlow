"""
Integration tests for ZFlow Advanced Features:
1. Knowledge Retrieval RAG Node & KnowledgeStore
2. ReAct Autonomous Agent Node (Tool Execution & Reasoning)
3. Human-in-the-Loop Approval Node
4. LLM Intent Router Node
"""
import asyncio
import os
import sys
import unittest

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server"))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from engine.context import ExecutionContext
from engine.graph import WorkflowGraph
from engine.runner import WorkflowRunner
from engine.knowledge_store import knowledge_store
from nodes.rag_node import RagNode
from nodes.agent_node import AgentNode
from nodes.human_input_node import HumanInputNode
from nodes.llm_router_node import LlmRouterNode
import nodes


class TestAdvancedFeatures(unittest.IsolatedAsyncioTestCase):

    def test_knowledge_store_hybrid_search(self):
        # Verify default seeded docs exist
        docs = knowledge_store.list_documents()
        self.assertGreaterEqual(len(docs), 2)

        # Search for warranty policy
        results = knowledge_store.search("chính sách đổi trả trong bao nhiêu ngày", top_k=2)
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("30 ngày", results[0]["content"])
        self.assertGreater(results[0]["score"], 0.2)
        print("RAG search verified:", results[0]["title"], f"(Score: {results[0]['score']})")

    async def test_rag_node_execution(self):
        rag = RagNode()
        ctx = ExecutionContext(session_id="rag_test", initial_variables={"query": "Gói Enterprise Pro bao nhiêu tiền một tháng?"})
        output = await rag.execute(inputs={"query": "Gói Enterprise Pro bao nhiêu tiền một tháng?"}, config={"top_k": 2}, context=ctx)

        self.assertTrue(output["has_match"])
        self.assertIn("1,500,000", output["context"])
        print("RagNode output context verified:\n", output["context"][:150], "...")

    async def test_react_agent_node(self):
        agent = AgentNode()
        ctx = ExecutionContext(session_id="agent_test", initial_variables={})
        output = await agent.execute(
            inputs={"query": "Tính giúp tôi chi phí gói Enterprise 12 tháng nếu giảm giá 10% (1500000 * 12 * 0.9)"},
            config={"provider": "simulator"},
            context=ctx
        )

        self.assertIn("response", output)
        self.assertIn("calculator", output.get("tools_used", []))
        self.assertGreaterEqual(len(output.get("intermediate_steps", [])), 1)
        print("ReAct Agent steps verified:", output["tools_used"])

    async def test_human_input_node_branching(self):
        hin = HumanInputNode()
        
        # Test Approved
        ctx_app = ExecutionContext(session_id="h1", initial_variables={"human_choice": "approved"})
        res_app = await hin.execute(inputs={"trigger_data": {"order_id": "ORD-999"}}, config={}, context=ctx_app)
        self.assertTrue(res_app["is_approved"])
        self.assertEqual(res_app["active_branch"], "approved_branch")
        self.assertIsNotNone(res_app["approved_branch"])
        self.assertIsNone(res_app["rejected_branch"])

        # Test Rejected
        ctx_rej = ExecutionContext(session_id="h2", initial_variables={"human_choice": "rejected"})
        res_rej = await hin.execute(inputs={"trigger_data": {"order_id": "ORD-999"}}, config={}, context=ctx_rej)
        self.assertFalse(res_rej["is_approved"])
        self.assertEqual(res_rej["active_branch"], "rejected_branch")
        self.assertIsNone(res_rej["approved_branch"])
        self.assertIsNotNone(res_rej["rejected_branch"])
        print("HumanInputNode branching verified.")

    async def test_llm_router_node(self):
        router = LlmRouterNode()
        
        # Sales intent
        ctx_sales = ExecutionContext(session_id="r1", initial_variables={})
        res_sales = await router.execute(
            inputs={"input_text": "Cho tôi hỏi báo giá chi tiết sản phẩm này với"},
            config={},
            context=ctx_sales
        )
        self.assertEqual(res_sales["active_branch"], "sales")

        # Tech support intent
        ctx_tech = ExecutionContext(session_id="r2", initial_variables={})
        res_tech = await router.execute(
            inputs={"input_text": "Phần mềm bị lỗi crash khi bấm đăng nhập, hướng dẫn tôi fix"},
            config={},
            context=ctx_tech
        )
        self.assertEqual(res_tech["active_branch"], "technical_support")
        print("LLM Intent Router classification verified.")


if __name__ == "__main__":
    unittest.main()
