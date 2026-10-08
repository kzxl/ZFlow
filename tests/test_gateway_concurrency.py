"""
Unit and Concurrency Tests for ZFlow API Gateway Node and High-Concurrency Dispatching:
1. Weighted A/B Canary Traffic Splitting
2. Round-Robin Load Balancing across multiple endpoints
3. Token Bucket Rate Limiting & Throttling
4. Circuit Breaker failure tripping and fallback routing
5. Simultaneous High-Concurrency Multi-Request Execution via asyncio.gather
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
from nodes.gateway_node import GatewayNode
from nodes.input_node import InputNode
from nodes.output_node import OutputNode


class TestGatewayAndConcurrency(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        GatewayNode.reset_all_limiters()

    def tearDown(self):
        GatewayNode.reset_all_limiters()
        self.loop.close()

    def test_01_weighted_ab_canary_distribution(self):
        """
        Tests weighted traffic distribution (e.g. 70% Route A, 30% Route B).
        """
        async def run_test():
            node = GatewayNode()
            config = {
                "strategy": "weighted_ab",
                "route_a_weight": 70,
                "route_b_weight": 30,
                "route_c_weight": 0
            }

            counts = {"route_a": 0, "route_b": 0, "route_c": 0}
            iterations = 200

            for i in range(iterations):
                ctx = ExecutionContext(session_id=f"ab_test_{i}")
                res = await node.execute({"input": f"Request {i}"}, config, ctx)
                branch = res["active_branch"]
                counts[branch] = counts.get(branch, 0) + 1

            # Route A should dominate (roughly 50% - 90%)
            self.assertGreater(counts["route_a"], counts["route_b"])
            self.assertEqual(counts["route_c"], 0)
            self.assertEqual(counts["route_a"] + counts["route_b"], iterations)

        self.loop.run_until_complete(run_test())

    def test_02_round_robin_load_balancing(self):
        """
        Tests round-robin sequential cycling across Route A, Route B, and Route C.
        """
        async def run_test():
            node = GatewayNode()
            config = {
                "strategy": "round_robin",
                "route_c_weight": 1  # enables route_c in round-robin pool
            }

            results = []
            for i in range(6):
                ctx = ExecutionContext(session_id=f"rr_sess_{i}")
                res = await node.execute({"input": f"Ping {i}"}, config, ctx)
                results.append(res["active_branch"])

            # Must alternate: route_a -> route_b -> route_c -> route_a -> route_b -> route_c
            expected = ["route_a", "route_b", "route_c", "route_a", "route_b", "route_c"]
            self.assertEqual(results, expected)

        self.loop.run_until_complete(run_test())

    def test_03_token_bucket_rate_limiter(self):
        """
        Tests token bucket rate limiting: permits burst capacity, then throttles subsequent requests.
        """
        async def run_test():
            node = GatewayNode()
            config = {
                "strategy": "rate_limiter",
                "rate_limit_rps": 2,
                "rate_limit_burst": 3,
                "throttle_message": "Chạm ngưỡng tần suất truy cập!"
            }

            client_session = "single_user_client"
            allowed_count = 0
            throttled_count = 0

            # Rapid burst of 6 requests
            for i in range(6):
                ctx = ExecutionContext(session_id=client_session)
                res = await node.execute({"input": f"Burst {i}"}, config, ctx)
                if res["active_branch"] == "route_a":
                    allowed_count += 1
                elif res["active_branch"] == "throttled":
                    throttled_count += 1
                    self.assertEqual(res["throttled"], "Chạm ngưỡng tần suất truy cập!")

            # Burst is 3, so first 3 should pass, remaining 3 should be throttled
            self.assertEqual(allowed_count, 3)
            self.assertEqual(throttled_count, 3)

        self.loop.run_until_complete(run_test())

    def test_04_circuit_breaker_tripping_and_fallback(self):
        """
        Tests Circuit Breaker tripping after consecutive failures, routing to fallback.
        """
        async def run_test():
            node = GatewayNode()
            config = {
                "strategy": "circuit_breaker",
                "circuit_failure_threshold": 2,
                "circuit_recovery_seconds": 10
            }

            ctx = ExecutionContext(session_id="cb_test")

            # 1. Initially CLOSED -> routes to route_a
            res1 = await node.execute({"input": "Healthy Request"}, config, ctx)
            self.assertEqual(res1["active_branch"], "route_a")

            # 2. Record 2 failures -> trips to OPEN
            GatewayNode.record_circuit_failure(threshold=2)
            GatewayNode.record_circuit_failure(threshold=2)

            # 3. Next execution should be diverted to fallback branch
            res_tripped = await node.execute({"input": "Degraded Request"}, config, ctx)
            self.assertEqual(res_tripped["active_branch"], "fallback")
            self.assertEqual(res_tripped["metrics"]["circuit_status"], "OPEN")

        self.loop.run_until_complete(run_test())

    def test_05_concurrent_multi_request_flow_execution(self):
        """
        Tests multiple requests hitting the workflow simultaneously using asyncio.gather.
        Verifies that WorkflowRunner safely executes concurrent requests with isolated contexts.
        """
        async def run_test():
            # Build a workflow with Gateway dispatching to 2 different output paths
            flow_def = {
                "nodes": [
                    {
                        "id": "gw_in",
                        "type": "input",
                        "title": "API Input",
                        "config": {"default_query": "Concurrent payload"}
                    },
                    {
                        "id": "gateway_node",
                        "type": "gateway",
                        "title": "Traffic Gateway",
                        "config": {
                            "strategy": "round_robin"
                        }
                    },
                    {
                        "id": "out_a",
                        "type": "output",
                        "title": "Channel A Output",
                        "config": {"output_key": "reply_a", "prefix": "[Route A Handler] "}
                    },
                    {
                        "id": "out_b",
                        "type": "output",
                        "title": "Channel B Output",
                        "config": {"output_key": "reply_b", "prefix": "[Route B Handler] "}
                    }
                ],
                "edges": [
                    {"id": "e1", "source": "gw_in", "target": "gateway_node", "sourceHandle": "query", "targetHandle": "input"},
                    {"id": "e2", "source": "gateway_node", "target": "out_a", "sourceHandle": "route_a", "targetHandle": "input"},
                    {"id": "e3", "source": "gateway_node", "target": "out_b", "sourceHandle": "route_b", "targetHandle": "input"}
                ]
            }

            graph = WorkflowGraph.from_dict(flow_def)

            async def execute_single_request(req_idx: int) -> Dict[str, Any]:
                runner = WorkflowRunner(max_steps=20)
                ctx = ExecutionContext(
                    session_id=f"concurrent_sess_{req_idx}",
                    initial_variables={"input": f"Data item #{req_idx}"}
                )
                return await runner.run(graph, ctx)

            # Fire 16 simultaneous requests
            tasks = [execute_single_request(i) for i in range(16)]
            results = await asyncio.gather(*tasks)

            self.assertEqual(len(results), 16)

            # Check outputs: 8 should be handled by Route A, 8 by Route B
            route_a_replies = [r["final_output"] for r in results if r["final_output"] and "[Route A Handler]" in r["final_output"]]
            route_b_replies = [r["final_output"] for r in results if r["final_output"] and "[Route B Handler]" in r["final_output"]]

            self.assertEqual(len(route_a_replies), 8)
            self.assertEqual(len(route_b_replies), 8)

        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
