"""
Unit & Integration Tests for System Settings and Active Workflow Dynamic Routing:
1. System Settings API (Persistence, Key Masking, Engine Configuration)
2. Active Workflow Dynamic Binding (/api/v1/flows/active/run & stream)
3. Dynamic Input Injection & Full Output Mapping Validation
4. Workflow I/O Schema Inspection (/api/v1/flows/active/schema)
"""
import os
import sys
import unittest
import json

SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server"))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from engine.settings_manager import settings_manager
from api.public_flows import resolve_target_flow, trigger_flow_api, get_flow_io_schema, FlowExecuteRequest
from api.settings import get_system_settings, update_system_settings, set_active_workflow, SettingsUpdatePayload, SetActiveFlowPayload


class TestSettingsAndActiveRoutes(unittest.IsolatedAsyncioTestCase):

    async def test_01_settings_manager_and_api(self):
        """Tests settings persistence, updating, and safe secret masking."""
        # 1. Update settings via payload
        update_payload = SettingsUpdatePayload(
            settings={
                "openai_api_key": "sk-proj-test1234567890abcdef",
                "default_model": "gpt-4o-mini",
                "default_temperature": 0.5,
                "memory_window_size": 8
            }
        )
        res_update = await update_system_settings(update_payload)
        self.assertEqual(res_update["status"], "saved")
        self.assertIn("openai_api_key", res_update["updated_keys"])

        # 2. Get settings with masking
        res_get_masked = await get_system_settings(raw_keys=False)
        self.assertTrue(res_get_masked["is_masked"])
        masked_key = res_get_masked["settings"]["openai_api_key"]
        self.assertIn("••••••••", masked_key)
        self.assertTrue(masked_key.startswith("sk-p"))
        print(f"✓ Settings API Masking Verified: '{masked_key}'")

        # 3. Direct retrieval from singleton
        raw_val = settings_manager.get("openai_api_key")
        self.assertEqual(raw_val, "sk-proj-test1234567890abcdef")
        print("✓ SettingsManager Persistence verified.")

    async def test_02_active_workflow_dynamic_routing(self):
        """Tests setting active flow and dynamically executing through /api/v1/flows/active/run."""
        # 1. Set active flow to intelligent_enterprise_chatbot_flow
        target_flow_id = "intelligent_enterprise_chatbot_flow"
        set_res = await set_active_workflow(SetActiveFlowPayload(flow_id=target_flow_id))
        self.assertEqual(set_res["status"], "success")
        self.assertEqual(set_res["active_flow_id"], target_flow_id)

        # 2. Resolve flow using 'active' alias
        resolved_id, flow_data = resolve_target_flow("active")
        self.assertEqual(resolved_id, target_flow_id)
        self.assertIn("Intelligent Enterprise Chatbot", flow_data.get("name", ""))
        print(f"✓ Dynamic Route Resolved 'active' -> '{resolved_id}' ({flow_data['name']})")

        # 3. Trigger Active Workflow with rich input payload
        req = FlowExecuteRequest(
            inputs={
                "query": "Tôi là Trần Tuấn, email tuan@corp.vn. Xin hãy giải thích quy định bảo mật thông tin nội bộ.",
                "user_role": "staff"
            },
            session_id="active_test_session"
        )
        run_res = await trigger_flow_api(flow_id="active", request=req)

        self.assertEqual(run_res["status"], "success")
        self.assertTrue(run_res["is_active_route"])
        self.assertEqual(run_res["flow_id"], target_flow_id)
        self.assertIn("reply", run_res["outputs"])
        self.assertIn("final_output", run_res["outputs"])
        print(f"✓ Active Flow Output received in {run_res['execution_time_ms']}ms -> '{str(run_res['outputs']['reply'])[:60]}...'")

    async def test_03_active_flow_schema_inspection(self):
        """Tests schema extraction for the currently active workflow."""
        schema_res = await get_flow_io_schema(flow_id="active")
        self.assertTrue(schema_res["is_active_route"])
        self.assertGreater(len(schema_res["inputs"]), 0)
        self.assertGreater(len(schema_res["outputs"]), 0)
        
        input_nodes = [i["node_type"] for i in schema_res["inputs"]]
        self.assertIn("input", input_nodes)
        
        output_keys = [o["output_key"] for o in schema_res["outputs"]]
        self.assertIn("reply", output_keys)
        print(f"✓ Active Flow Schema verified: {len(schema_res['inputs'])} inputs, {len(schema_res['outputs'])} outputs.")


if __name__ == "__main__":
    unittest.main()
