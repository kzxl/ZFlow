"""
Integration and Unit Tests for ZFlow Conversation Memory & SQLite Store.
Tests memory persistence, sliding window, token budget, summary buffer strategies,
and multi-turn contextual recall across sequential workflow executions.
"""
import asyncio
import os
import sys
import unittest
import time
import shutil

# Add server directory to sys.path
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server"))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from engine.memory_store import SessionMemoryStore
from engine.graph import WorkflowGraph
from engine.context import ExecutionContext
from engine.runner import WorkflowRunner
from nodes.memory_node import MemoryNode
from nodes.prompt_node import PromptNode
from nodes.input_node import InputNode
from nodes.output_node import OutputNode
from nodes.llm_node import LlmNode
import nodes # register all nodes

class TestConversationMemory(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_db_path = os.path.join(os.path.dirname(__file__), "test_chat_memory.db")
        self.store = SessionMemoryStore(db_path=self.test_db_path)
        self.store.clear_all()

    def tearDown(self):
        self.store.clear_all()

    def test_sqlite_persistence_and_stats(self):
        session_id = "test_sess_001"
        self.store.append_message(session_id, "user", "Xin chào ZFlow!")
        self.store.append_message(session_id, "assistant", "Chào bạn, tôi có thể giúp gì cho bạn?")
        self.store.append_message(session_id, "user", "Tôi muốn tìm hiểu về cơ chế Memory.")

        history = self.store.get_history(session_id)
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Xin chào ZFlow!")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[2]["role"], "user")

        # Test session stats
        stats = self.store.get_session_stats(session_id)
        self.assertEqual(stats["turn_count"], 3)
        self.assertEqual(stats["user_turns"], 2)
        self.assertEqual(stats["assistant_turns"], 1)
        self.assertGreater(stats["total_chars"], 50)

        # Test list_sessions
        sessions = self.store.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], session_id)
        self.assertEqual(sessions[0]["turn_count"], 3)
        self.assertIn("cơ chế Memory", sessions[0]["last_message"])

        # Test clear_session
        self.store.clear_session(session_id)
        history_after_clear = self.store.get_history(session_id)
        self.assertEqual(len(history_after_clear), 0)

    async def test_memory_node_strategies(self):
        session_id = "strat_sess_002"
        # Seed 10 dialog turns
        for i in range(1, 11):
            role = "user" if i % 2 == 1 else "assistant"
            self.store.append_message(session_id, role, f"Turn message {i} content text")

        memory_node = MemoryNode()

        # 1. Sliding Window Strategy (window_size = 4)
        ctx1 = ExecutionContext(session_id=session_id)
        res1 = await memory_node.execute(
            inputs={},
            config={"strategy": "sliding_window", "window_size": 4, "storage_backend": "sqlite_persistent"},
            context=ctx1
        )
        self.assertEqual(len(res1["chat_history"]), 4)
        self.assertEqual(res1["chat_history"][-1]["content"], "Turn message 10 content text")
        self.assertEqual(res1["turn_count"], 10)
        self.assertIn("User: Turn message 7", res1["formatted_history"])

        # 2. Token Budget Strategy (low budget)
        ctx2 = ExecutionContext(session_id=session_id)
        res2 = await memory_node.execute(
            inputs={},
            config={"strategy": "token_budget", "max_token_budget": 25, "storage_backend": "sqlite_persistent"},
            context=ctx2
        )
        # 25 tokens ~ 100 chars, each message is ~30 chars => should keep 2-3 messages
        self.assertLessEqual(len(res2["chat_history"]), 4)
        self.assertGreaterEqual(len(res2["chat_history"]), 1)

        # 3. Summary Buffer Strategy
        ctx3 = ExecutionContext(session_id=session_id)
        res3 = await memory_node.execute(
            inputs={},
            config={"strategy": "summary_buffer", "window_size": 4, "storage_backend": "sqlite_persistent"},
            context=ctx3
        )
        self.assertEqual(len(res3["chat_history"]), 4)
        self.assertTrue(len(res3["summary"]) > 0)
        self.assertIn("Tóm tắt ngữ cảnh trước", res3["formatted_history"])

        # 4. Full History Strategy
        ctx4 = ExecutionContext(session_id=session_id)
        res4 = await memory_node.execute(
            inputs={},
            config={"strategy": "full_history", "storage_backend": "sqlite_persistent"},
            context=ctx4
        )
        self.assertEqual(len(res4["chat_history"]), 10)

    async def test_multi_turn_conversational_workflow(self):
        """
        Tests end-to-end multi-turn conversation flow with MemoryNode, PromptNode, and LLMNode.
        Turn 1: User introduces name and role.
        Turn 2: Memory recovers Turn 1, LLM context includes prior name and role.
        """
        session_id = f"e2e_conv_{int(time.time())}"
        
        flow_def = {
            "id": "conversational_memory_pipeline",
            "nodes": [
                {
                    "id": "node_input",
                    "type": "input",
                    "title": "User Query",
                    "position": {"x": 100, "y": 200},
                    "data": {"config": {}}
                },
                {
                    "id": "node_memory",
                    "type": "memory",
                    "title": "Conversation Memory",
                    "position": {"x": 350, "y": 200},
                    "data": {"config": {"strategy": "sliding_window", "window_size": 6}}
                },
                {
                    "id": "node_prompt",
                    "type": "prompt",
                    "title": "Prompt Template",
                    "position": {"x": 650, "y": 200},
                    "data": {
                        "config": {
                            "system_template": "Bạn là AI trợ lý ghi nhớ ngữ cảnh.",
                            "user_template": "Lịch sử cuộc hội thoại trước:\n{formatted_history}\n\nTin nhắn người dùng hiện tại:\n{query}"
                        }
                    }
                },
                {
                    "id": "node_llm",
                    "type": "llm",
                    "title": "LLM Inference",
                    "position": {"x": 950, "y": 200},
                    "data": {"config": {"provider": "simulator", "model": "gpt-4o-mini"}}
                },
                {
                    "id": "node_output",
                    "type": "output",
                    "title": "Output Response",
                    "position": {"x": 1250, "y": 200},
                    "data": {"config": {}}
                }
            ],
            "edges": [
                {"id": "e1", "source": "node_input", "target": "node_memory", "sourceHandle": "session_id", "targetHandle": "session_id"},
                {"id": "e2", "source": "node_memory", "target": "node_prompt", "sourceHandle": "formatted_history", "targetHandle": "context_data"},
                {"id": "e3", "source": "node_prompt", "target": "node_llm", "sourceHandle": "prompt", "targetHandle": "prompt"},
                {"id": "e4", "source": "node_llm", "target": "node_output", "sourceHandle": "text", "targetHandle": "response_text"}
            ]
        }

        graph = WorkflowGraph.from_dict(flow_def)
        runner = WorkflowRunner()

        # Turn 1
        query_1 = "Tôi tên là Hoàng, kiến trúc sư phần mềm."
        ctx_turn1 = ExecutionContext(session_id=session_id, initial_variables={"input": query_1, "query": query_1})
        res1 = await runner.run(graph, ctx_turn1)
        
        reply_1 = res1.get("final_output")
        self.assertIsNotNone(reply_1)

        # Simulate auto-persisting Turn 1
        from engine.memory_store import memory_store
        memory_store.append_message(session_id, "user", query_1)
        memory_store.append_message(session_id, "assistant", reply_1)

        # Verify storage has 2 turns
        hist_1 = memory_store.get_history(session_id)
        self.assertEqual(len(hist_1), 2)

        # Turn 2
        query_2 = "Bạn có nhớ tôi tên là gì và làm nghề gì không?"
        ctx_turn2 = ExecutionContext(session_id=session_id, initial_variables={"input": query_2, "query": query_2})
        res2 = await runner.run(graph, ctx_turn2)

        prompt_in_turn2 = ctx_turn2.get_variable("prompt")
        self.assertIn("Hoàng", prompt_in_turn2)
        self.assertIn("kiến trúc sư phần mềm", prompt_in_turn2)
        print("\nTurn 2 interpolated prompt with memory successfully recalled:\n", prompt_in_turn2[:200])

if __name__ == "__main__":
    unittest.main()
