"""
Automated Test Suite for ZFlow Advanced Enterprise Features:
1. Multi-Model Failover & Resilient Streaming
2. Sub-Flow / Nested Workflow Composite Node
3. Webhook Trigger Node & Public Endpoint Security
4. Execution Waterfall Timeline & Token/Cost Inspector
"""
import unittest
import asyncio
import os
import sys
import json
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from engine.context import ExecutionContext
from engine.graph import WorkflowGraph
from engine.runner import WorkflowRunner, estimate_token_cost
from nodes.llm_node import LlmNode
from nodes.subflow_node import SubflowNode
from nodes.webhook_node import WebhookTriggerNode
from nodes.output_node import OutputNode
from api.workflows import save_flow_data, load_flow_data
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestAdvancedEnterpriseSuite(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_01_token_cost_estimation(self):
        """
        Tests blended token cost calculations across model tiers.
        """
        self.assertEqual(estimate_token_cost("simulator", 1000), 0.0)
        self.assertEqual(estimate_token_cost("llama3.1:8b", 5000), 0.0)
        
        # gpt-4o-mini: 1M tokens -> ~$0.35
        mini_cost = estimate_token_cost("gpt-4o-mini", 1_000_000)
        self.assertAlmostEqual(mini_cost, 0.35, places=4)

        # gpt-4o: 100,000 tokens -> ~$0.50
        gpt4o_cost = estimate_token_cost("gpt-4o", 100_000)
        self.assertAlmostEqual(gpt4o_cost, 0.50, places=4)

        # deepseek: 1,000,000 tokens -> ~$0.20
        ds_cost = estimate_token_cost("deepseek-chat", 1_000_000)
        self.assertAlmostEqual(ds_cost, 0.20, places=4)

    def test_02_llm_multi_model_failover_to_simulator(self):
        """
        Verifies that when primary model connection fails, LlmNode automatically
        falls over to the backup simulator candidate without breaking workflow.
        """
        async def run_test():
            node = LlmNode()
            context = ExecutionContext(session_id="test_failover_sess")
            inputs = {"prompt": "Khủng hoảng mô hình LLM chính"}
            
            # Configure primary model with invalid base url to force connection error,
            # but specify simulator in fallback_models
            config = {
                "provider": "openai_compatible",
                "model": "gpt-4o",
                "api_base": "http://127.0.0.1:9999/invalid",
                "api_key": "dummy_key",
                "timeout_seconds": 1.0,
                "enable_fallback": True,
                "fallback_models": "deepseek-chat, simulator"
            }

            tokens = []
            async for chunk in node.execute_stream(inputs, config, context):
                if chunk.get("type") == "token":
                    tokens.append(chunk.get("token", ""))

            full_reply = "".join(tokens)
            # Must indicate failover notice and successfully output simulator content
            self.assertTrue(len(tokens) > 5)
            self.assertTrue("Failover" in full_reply or "simulator" in full_reply.lower() or "ZFlow" in full_reply)

        self.loop.run_until_complete(run_test())

    def test_03_subflow_execution_and_circular_protection(self):
        """
        Tests embedding a subflow into another workflow and verifies circular dependency safeguards.
        """
        async def run_test():
            # 1. Create and save a dedicated child flow
            child_flow_id = "unit_child_flow"
            child_flow_data = {
                "name": "Unit Child Flow",
                "nodes": [
                    {
                        "id": "c_in",
                        "type": "input",
                        "data": {"title": "Child In", "config": {}},
                        "position": {"x": 0, "y": 0}
                    },
                    {
                        "id": "c_out",
                        "type": "output",
                        "data": {"title": "Child Out", "config": {"output_key": "reply"}},
                        "position": {"x": 200, "y": 0}
                    }
                ],
                "edges": [
                    {"id": "c_e1", "source": "c_in", "target": "c_out", "sourceHandle": "query", "targetHandle": "input"}
                ]
            }
            save_flow_data(child_flow_id, child_flow_data)

            # 2. Execute SubflowNode directly
            subflow_node = SubflowNode()
            parent_context = ExecutionContext(session_id="parent_sess")
            res = await subflow_node.execute(
                inputs={"input": "Hello from Parent Flow!"},
                config={"subflow_id": child_flow_id, "inherit_context": True},
                context=parent_context
            )

            self.assertIn("output", res)
            self.assertEqual(res["output"], "Hello from Parent Flow!")

            # 3. Test circular invocation safety
            cyclic_context = ExecutionContext(
                session_id="cyclic_sess",
                initial_variables={"_subflow_call_stack": [child_flow_id, child_flow_id]}
            )
            cyclic_res = await subflow_node.execute(
                inputs={"input": "Recursive loop attempt"},
                config={"subflow_id": child_flow_id},
                context=cyclic_context
            )
            self.assertIn("Circular subflow dependency", str(cyclic_res.get("output", "")))

        self.loop.run_until_complete(run_test())

    def test_04_webhook_trigger_node_and_public_endpoint(self):
        """
        Tests WebhookTriggerNode parameter extraction and the /api/v1/webhook/{hook_id} endpoint.
        """
        # 1. Test WebhookTriggerNode local execution
        async def run_node_test():
            node = WebhookTriggerNode()
            ctx = ExecutionContext(session_id="hook_sess", initial_variables={
                "webhook_payload": {"message": "GitHub commit pushed to main", "sender": "kzxl"},
                "webhook_headers": {"x-github-event": "push"}
            })
            result = await node.execute({}, {"hook_id": "test_hook"}, ctx)
            self.assertEqual(result["event"], "push")
            self.assertEqual(result["query"], "GitHub commit pushed to main")
            self.assertEqual(ctx.get_variable("input"), "GitHub commit pushed to main")

        self.loop.run_until_complete(run_node_test())

        # 2. Test Public Webhook API Endpoint: /api/v1/webhook/{hook_id}
        # First save a workflow with a Webhook node having a secret token
        webhook_flow_id = "test_webhook_flow"
        wf_data = {
            "name": "Webhook Flow",
            "nodes": [
                {
                    "id": "hook_node",
                    "type": "webhook",
                    "data": {
                        "title": "Stripe Hook",
                        "config": {
                            "hook_id": "stripe_invoice",
                            "secret_token": "secret_12345"
                        }
                    },
                    "position": {"x": 0, "y": 0}
                },
                {
                    "id": "out_node",
                    "type": "output",
                    "data": {"title": "Out", "config": {"output_key": "reply"}},
                    "position": {"x": 200, "y": 0}
                }
            ],
            "edges": [
                {"id": "e_hook", "source": "hook_node", "target": "out_node", "sourceHandle": "query", "targetHandle": "input"}
            ]
        }
        save_flow_data(webhook_flow_id, wf_data)

        # Unauthorized request (wrong secret token)
        res_unauth = client.post(
            f"/api/v1/webhook/stripe_invoice?flow_id={webhook_flow_id}",
            headers={"x-webhook-secret": "wrong_key"},
            json={"message": "Invoice paid"}
        )
        self.assertEqual(res_unauth.status_code, 401)

        # Authorized request (correct secret token)
        res_auth = client.post(
            f"/api/v1/webhook/stripe_invoice?flow_id={webhook_flow_id}",
            headers={"x-webhook-secret": "secret_12345"},
            json={"message": "Invoice #999 paid $150"}
        )
        self.assertEqual(res_auth.status_code, 200)
        data = res_auth.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["hook_id"], "stripe_invoice")
        self.assertIn("Invoice #999 paid $150", data["outputs"]["reply"])

    def test_05_waterfall_timeline_and_cost_benchmarks(self):
        """
        Tests WorkflowRunner waterfall benchmark calculation, offsets, and economics metrics.
        """
        async def run_test():
            # Build simple 2-node graph: input -> output
            graph_dict = {
                "nodes": [
                    {
                        "id": "n1",
                        "type": "input",
                        "title": "Start",
                        "config": {"default_query": "Testing Waterfall"}
                    },
                    {
                        "id": "n2",
                        "type": "output",
                        "title": "End",
                        "config": {"output_key": "reply"}
                    }
                ],
                "edges": [
                    {"id": "e1", "source": "n1", "target": "n2", "sourceHandle": "query", "targetHandle": "input"}
                ]
            }
            graph = WorkflowGraph.from_dict(graph_dict)
            context = ExecutionContext(session_id="wf_benchmark_test")

            runner = WorkflowRunner(max_steps=10)
            res = await runner.run(graph, context)

            self.assertIn("benchmarks", res)
            bm = res["benchmarks"]
            self.assertIn("total_time_ms", bm)
            self.assertIn("nodes", bm)
            self.assertEqual(len(bm["nodes"]), 2)

            node1_bm = bm["nodes"][0]
            self.assertEqual(node1_bm["node_id"], "n1")
            self.assertGreaterEqual(node1_bm["start_offset_ms"], 0)
            self.assertGreaterEqual(node1_bm["duration_ms"], 0)
            self.assertEqual(node1_bm["status"], "success")

            node2_bm = bm["nodes"][1]
            self.assertEqual(node2_bm["node_id"], "n2")
            # node 2 must start after or at same time as node 1 start
            self.assertGreaterEqual(node2_bm["start_offset_ms"], node1_bm["start_offset_ms"])

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
