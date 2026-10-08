"""
Unit Tests for ZFlow Universal Payload Envelope:
Ensures workflows are decoupled from specific business domains and can handle:
1. Plain conversational chat inputs (task_type = 'chat')
2. Structured JSON string inputs auto-parsed into payloads (task_type = 'data_pipeline' / 'api')
3. Direct dictionary payloads with custom metadata and token bindings
4. WebhookTriggerNode multi-purpose envelope forwarding
5. Zero pollution of chat history for non-chat data payloads
"""
import unittest
import asyncio
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from engine.context import ExecutionContext
from nodes.input_node import InputNode
from nodes.webhook_node import WebhookTriggerNode
from engine.auth_manager import auth_manager


class TestUniversalPayloadEnvelope(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_01_plain_text_conversational_input(self):
        """
        Tests standard conversational text query defaults to chat task_type and appends to chat history.
        """
        async def run_test():
            node = InputNode()
            ctx = ExecutionContext(session_id="chat_session_01", initial_variables={"input": "Xin chào ZFlow!"})
            
            res = await node.execute({}, {}, ctx)
            self.assertEqual(res["task_type"], "chat")
            self.assertEqual(res["query"], "Xin chào ZFlow!")
            self.assertEqual(res["payload"], {"text": "Xin chào ZFlow!"})
            self.assertEqual(res["metadata"]["session_id"], "chat_session_01")
            # Chat history must have 1 user message
            self.assertEqual(len(ctx.chat_history), 1)
            self.assertEqual(ctx.chat_history[0]["content"], "Xin chào ZFlow!")

        self.loop.run_until_complete(run_test())

    def test_02_structured_json_string_input(self):
        """
        Tests that an incoming JSON string is automatically parsed into a structured payload dictionary,
        extracts explicit task_type, and does NOT pollute chat history if not a chat task.
        """
        async def run_test():
            node = InputNode()
            raw_json = json.dumps({
                "task_type": "data_pipeline",
                "action": "aggregate_sales",
                "records": [{"id": 1, "amount": 100}, {"id": 2, "amount": 250}],
                "metadata": {"tenant_id": "org_erp_09", "priority": "high"},
                "query": "Báo cáo tổng hợp doanh số quý 1"
            })
            ctx = ExecutionContext(session_id="pipeline_sess_02", initial_variables={"input": raw_json})

            res = await node.execute({}, {}, ctx)
            self.assertEqual(res["task_type"], "data_pipeline")
            self.assertEqual(res["query"], "Báo cáo tổng hợp doanh số quý 1")
            self.assertTrue(isinstance(res["payload"], dict))
            self.assertEqual(len(res["payload"]["records"]), 2)
            self.assertEqual(res["metadata"]["tenant_id"], "org_erp_09")
            self.assertEqual(res["metadata"]["priority"], "high")

            # Since task_type != 'chat', chat history should remain unpolluted
            self.assertEqual(len(ctx.chat_history), 0)

        self.loop.run_until_complete(run_test())

    def test_03_direct_dict_payload_with_token(self):
        """
        Tests dictionary payload passed directly through API with bound JWT Access Token.
        """
        async def run_test():
            token_bundle = auth_manager.issue_access_token(user_id="service_account_sync", role="admin")
            token = token_bundle["access_token"]

            node = InputNode()
            dict_payload = {
                "purpose": "media_gen",
                "prompt": "Cyberpunk neon street at night",
                "width": 1024,
                "height": 1024
            }
            ctx = ExecutionContext(
                session_id="media_sess_03",
                initial_variables={"input": dict_payload, "access_token": token}
            )

            res = await node.execute({}, {}, ctx)
            self.assertEqual(res["task_type"], "media_gen")
            self.assertEqual(res["query"], "Cyberpunk neon street at night")
            self.assertEqual(res["payload"]["width"], 1024)
            self.assertEqual(res["access_token"], token)
            self.assertEqual(ctx.get_variable("access_token"), token)

        self.loop.run_until_complete(run_test())

    def test_04_webhook_universal_envelope(self):
        """
        Tests WebhookTriggerNode extracts task_type, payload, metadata, and token.
        """
        async def run_test():
            node = WebhookTriggerNode()
            ctx = ExecutionContext(session_id="wh_envelope_sess")
            ctx.set_variable("webhook_payload", {
                "event": "customer.created",
                "task_type": "crm_sync",
                "customer_id": "CUST_9918",
                "metadata": {"origin": "shopify"}
            })
            ctx.set_variable("webhook_headers", {
                "content-type": "application/json",
                "authorization": "Bearer dummy_test_token"
            })

            res = await node.execute({}, {"hook_id": "shopify_customers"}, ctx)
            self.assertEqual(res["task_type"], "crm_sync")
            self.assertEqual(res["event"], "customer.created")
            self.assertEqual(res["payload"]["customer_id"], "CUST_9918")
            self.assertEqual(res["metadata"]["origin"], "shopify")
            self.assertEqual(res["metadata"]["hook_id"], "shopify_customers")
            self.assertEqual(res["access_token"], "dummy_test_token")
            self.assertEqual(ctx.get_variable("task_type"), "crm_sync")

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
