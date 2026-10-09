"""
Unit tests for ZFlow Live Telemetry & Traffic Observability Engine.
Verifies thread-safe counters, sliding RPS, in-flight tracking, and API endpoints.
"""
import unittest
import asyncio
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))

from engine.telemetry import TelemetryManager, telemetry_manager
from engine.graph import WorkflowGraph
from engine.context import ExecutionContext
from engine.runner import WorkflowRunner
from main import app
from fastapi.testclient import TestClient


class TestTelemetryEngine(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.mgr = TelemetryManager()
        telemetry_manager.reset()
        self.client = TestClient(app)

    def tearDown(self):
        telemetry_manager.reset()
        self.loop.close()

    def test_workflow_lifecycle_tracking(self):
        """Test workflow and node lifecycle events properly update counters and latency."""
        wf_id = "test-flow-1"
        session_id = "sess-001"
        user_id = "usr-vip"

        # 1. Start workflow
        self.mgr.on_workflow_start(wf_id, session_id, user_id)
        self.assertEqual(self.mgr.total_in_flight, 1)
        self.assertEqual(self.mgr.workflow_in_flight[wf_id], 1)
        self.assertIn(session_id, self.mgr.active_requests)
        self.assertEqual(self.mgr.active_requests[session_id]["user_id"], user_id)

        # 2. Node start
        self.mgr.on_node_start(wf_id, "node_input", session_id)
        self.assertEqual(self.mgr.nodes["node_input"].in_flight, 1)
        self.assertEqual(self.mgr.active_requests[session_id]["current_node_id"], "node_input")

        # 3. Node end
        time.sleep(0.01)  # small delta for duration
        self.mgr.on_node_end(wf_id, "node_input", session_id, duration_ms=12.5, is_error=False)
        self.assertEqual(self.mgr.nodes["node_input"].in_flight, 0)
        self.assertEqual(self.mgr.nodes["node_input"].total_completed, 1)
        self.assertGreater(self.mgr.nodes["node_input"].avg_duration_ms, 0.0)

        # 4. Workflow end
        self.mgr.on_workflow_end(wf_id, session_id, is_error=False)
        self.assertEqual(self.mgr.total_in_flight, 0)
        self.assertEqual(self.mgr.workflow_in_flight[wf_id], 0)
        self.assertEqual(self.mgr.total_completed_requests, 1)

    def test_congestion_and_heat_status(self):
        """Test that high node in-flight requests trigger 'busy' or 'congested' heat status."""
        node_id = "heavy_llm_node"
        wf_id = "flow_load"

        # Simulate 8 concurrent requests on the same node
        for i in range(8):
            s_id = f"sess-{i}"
            self.mgr.on_workflow_start(wf_id, s_id, "u1")
            self.mgr.on_node_start(wf_id, node_id, s_id)

        snapshot = self.mgr.get_snapshot(flow_id=wf_id)
        self.assertEqual(snapshot["total_in_flight"], 8)
        self.assertIn(node_id, snapshot["nodes"])
        self.assertEqual(snapshot["nodes"][node_id]["in_flight"], 8)
        # 8 in-flight should exceed congested threshold (>= 8)
        self.assertEqual(snapshot["nodes"][node_id]["heat_status"], "congested")

        # Drain 5 requests -> leaving 3
        for i in range(5):
            s_id = f"sess-{i}"
            self.mgr.on_node_end(wf_id, node_id, s_id, duration_ms=50.0, is_error=False)
            self.mgr.on_workflow_end(wf_id, s_id, is_error=False)

        snapshot2 = self.mgr.get_snapshot(flow_id=wf_id)
        # 3 in-flight -> busy
        self.assertEqual(snapshot2["nodes"][node_id]["in_flight"], 3)
        self.assertEqual(snapshot2["nodes"][node_id]["heat_status"], "busy")

    def test_snapshot_filtering(self):
        """Test snapshot correctly scopes metrics when filtered by flow_id."""
        self.mgr.on_workflow_start("flow_A", "s1", "u1")
        self.mgr.on_workflow_start("flow_B", "s2", "u2")

        snap_a = self.mgr.get_snapshot(flow_id="flow_A")
        self.assertEqual(snap_a["workflow_in_flight"], 1)
        self.assertEqual(len(snap_a["active_requests"]), 1)
        self.assertEqual(snap_a["active_requests"][0]["flow_id"], "flow_A")

        snap_all = self.mgr.get_snapshot()
        self.assertEqual(snap_all["total_in_flight"], 2)
        self.assertEqual(len(snap_all["active_requests"]), 2)

    def test_telemetry_api_endpoints(self):
        """Test REST API endpoints for telemetry."""
        # 1. Initial snapshot
        resp = self.client.get("/api/v1/telemetry/snapshot")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_in_flight"], 0)
        self.assertIn("nodes", data)
        self.assertIn("current_rps", data)

        # 2. Trigger an event via global manager
        telemetry_manager.on_workflow_start("flow-demo", "sess-test", "user-test")
        telemetry_manager.on_node_start("flow-demo", "node-1", "sess-test")

        # Snapshot check
        resp2 = self.client.get("/api/v1/telemetry/snapshot?flow_id=flow-demo")
        self.assertEqual(resp2.status_code, 200)
        d2 = resp2.json()
        self.assertEqual(d2["total_in_flight"], 1)
        self.assertEqual(d2["workflow_in_flight"], 1)
        self.assertIn("node-1", d2["nodes"])
        self.assertEqual(d2["nodes"]["node-1"]["in_flight"], 1)

        # Active requests check
        resp_act = self.client.get("/api/v1/telemetry/active-requests?flow_id=flow-demo")
        self.assertEqual(resp_act.status_code, 200)
        act_data = resp_act.json()
        self.assertEqual(act_data["count"], 1)
        self.assertEqual(act_data["active_requests"][0]["session_id"], "sess-test")

        # Reset endpoint
        resp_rst = self.client.post("/api/v1/telemetry/reset")
        self.assertEqual(resp_rst.status_code, 200)
        self.assertEqual(telemetry_manager.total_in_flight, 0)

    def test_runner_telemetry_integration(self):
        """Test WorkflowRunner runs seamlessly with telemetry hooks enabled."""
        async def run_flow():
            flow_data = {
                "nodes": [
                    {
                        "id": "node_in",
                        "type": "input",
                        "title": "Input Node",
                        "data": {"default_input": "hello telemetry"}
                    }
                ],
                "edges": []
            }
            graph = WorkflowGraph.from_dict(flow_data)
            context = ExecutionContext(session_id="run-telemetry-1", initial_variables={"input": "test payload", "flow_id": "test_flow"})
            runner = WorkflowRunner()
            result = await runner.run(graph, context)
            return result

        result = self.loop.run_until_complete(run_flow())
        self.assertIsNotNone(result)

        # Telemetry should register node completed count
        snap = telemetry_manager.get_snapshot(flow_id="test_flow")
        self.assertIn("node_in", snap["nodes"])
        self.assertEqual(snap["nodes"]["node_in"]["total_completed"], 1)
        self.assertEqual(snap["nodes"]["node_in"]["in_flight"], 0)


if __name__ == "__main__":
    unittest.main()
