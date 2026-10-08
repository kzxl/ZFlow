"""
API Gateway & Traffic Dispatcher Node for ZFlow.
Handles high-concurrency traffic management, load balancing (Round-Robin, Weighted A/B Canary),
Token Bucket Rate Limiting / Throttling, and Circuit Breaker failover.
"""
from typing import Dict, Any, AsyncGenerator, List, Tuple
import time
import random
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

# Global in-memory state stores for Gateway instances across requests
_GATEWAY_RR_COUNTERS: Dict[str, int] = {}
_GATEWAY_CIRCUIT_STATES: Dict[str, Dict[str, Any]] = {}
_GATEWAY_RATE_LIMITERS: Dict[str, Dict[str, Any]] = {}


@NodeRegistry.register
class GatewayNode(BaseNode):
    node_type = "gateway"
    name = "API Gateway & Dispatcher"
    category = "logic"
    description = "Điều tiết lưu lượng, phân luồng A/B Testing, cân bằng tải Round-Robin, giới hạn tốc độ (Rate Limiter) và Cầu dao tự ngắt (Circuit Breaker)."
    icon = "Network"

    inputs = [
        PortDef(name="input", data_type="any", label="Incoming Request / Query", required=True),
        PortDef(name="context", data_type="object", label="Request Context / Headers", required=False)
    ]

    outputs = [
        PortDef(name="route_a", data_type="any", label="🔀 Route A (Primary / Canary High)"),
        PortDef(name="route_b", data_type="any", label="🔀 Route B (Secondary / Canary Low)"),
        PortDef(name="route_c", data_type="any", label="🔀 Route C (Tertiary / Free Tier)"),
        PortDef(name="throttled", data_type="any", label="⏳ Throttled (Rate Limit Exceeded)"),
        PortDef(name="fallback", data_type="any", label="🛡️ Fallback (Circuit Open)"),
        PortDef(name="active_branch", data_type="string", label="Active Dispatch Handle"),
        PortDef(name="metrics", data_type="object", label="Gateway Dispatch Metrics")
    ]

    config_schema = {
        "strategy": {
            "type": "select",
            "label": "Dispatch Strategy",
            "options": [
                "weighted_ab",
                "round_robin",
                "rate_limiter",
                "circuit_breaker",
                "priority_tier"
            ],
            "default": "weighted_ab"
        },
        "route_a_weight": {
            "type": "number",
            "label": "Route A Weight (Percentage)",
            "min": 0,
            "max": 100,
            "default": 80
        },
        "route_b_weight": {
            "type": "number",
            "label": "Route B Weight (Percentage)",
            "min": 0,
            "max": 100,
            "default": 20
        },
        "route_c_weight": {
            "type": "number",
            "label": "Route C Weight (Percentage)",
            "min": 0,
            "max": 100,
            "default": 0
        },
        "rate_limit_rps": {
            "type": "number",
            "label": "Rate Limit (Requests per Second)",
            "min": 1,
            "max": 10000,
            "default": 10
        },
        "rate_limit_burst": {
            "type": "number",
            "label": "Burst Capacity",
            "min": 1,
            "max": 50000,
            "default": 20
        },
        "circuit_failure_threshold": {
            "type": "number",
            "label": "Circuit Breaker Failure Threshold",
            "min": 1,
            "max": 50,
            "default": 3
        },
        "circuit_recovery_seconds": {
            "type": "number",
            "label": "Circuit Recovery Cooldown (Seconds)",
            "min": 1,
            "max": 300,
            "default": 15
        },
        "priority_key": {
            "type": "string",
            "label": "User Tier Context Variable Name",
            "default": "user_tier"
        },
        "throttle_message": {
            "type": "string",
            "label": "Throttled Notice Message",
            "default": "⏳ [API Gateway]: Lưu lượng truy cập đang vượt quá ngưỡng cho phép (Rate Limit Exceeded). Yêu cầu đã được phân luồng điều tiết."
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Evaluates incoming traffic, applies rate limiting and load balancing policies,
        and dispatches payload to the active destination branch.
        """
        query_input = inputs.get("input")
        if query_input is None:
            query_input = context.get_variable("input") or context.get_variable("query", "")

        strategy = config.get("strategy", "weighted_ab")
        client_key = context.session_id or "global_client"
        node_instance_id = "default_gateway"

        active_branch = "route_a"
        dispatched_reason = ""
        throttle_triggered = False
        circuit_status = "CLOSED"

        # 1. Rate Limiting Strategy (Token Bucket)
        if strategy == "rate_limiter":
            rps = float(config.get("rate_limit_rps", 10))
            burst = float(config.get("rate_limit_burst", 20))
            is_allowed, rem_tokens = self._check_rate_limit(client_key, rps, burst)
            if not is_allowed:
                active_branch = "throttled"
                throttle_triggered = True
                dispatched_reason = f"Rate limit exceeded (Tokens: {rem_tokens:.2f}/{burst})"
            else:
                active_branch = "route_a"
                dispatched_reason = f"Rate limit passed (Remaining tokens: {rem_tokens:.2f})"

        # 2. Weighted A/B / Canary Testing Strategy
        elif strategy == "weighted_ab":
            w_a = max(0, int(config.get("route_a_weight", 80)))
            w_b = max(0, int(config.get("route_b_weight", 20)))
            w_c = max(0, int(config.get("route_c_weight", 0)))
            total = w_a + w_b + w_c
            if total <= 0:
                active_branch = "route_a"
            else:
                rand_val = random.uniform(0, total)
                if rand_val < w_a:
                    active_branch = "route_a"
                    dispatched_reason = f"Canary Route A chosen ({w_a}/{total} weight)"
                elif rand_val < (w_a + w_b):
                    active_branch = "route_b"
                    dispatched_reason = f"Canary Route B chosen ({w_b}/{total} weight)"
                else:
                    active_branch = "route_c"
                    dispatched_reason = f"Canary Route C chosen ({w_c}/{total} weight)"

        # 3. Round-Robin Load Balancing
        elif strategy == "round_robin":
            available_routes = ["route_a", "route_b"]
            if int(config.get("route_c_weight", 0)) > 0:
                available_routes.append("route_c")

            current_count = _GATEWAY_RR_COUNTERS.get(node_instance_id, 0)
            chosen_idx = current_count % len(available_routes)
            active_branch = available_routes[chosen_idx]
            _GATEWAY_RR_COUNTERS[node_instance_id] = current_count + 1
            dispatched_reason = f"Round-Robin turn #{current_count + 1} -> {active_branch}"

        # 4. Circuit Breaker Strategy
        elif strategy == "circuit_breaker":
            fail_threshold = int(config.get("circuit_failure_threshold", 3))
            cooldown_sec = float(config.get("circuit_recovery_seconds", 15))
            active_branch, circuit_status, dispatched_reason = self._evaluate_circuit_breaker(
                node_instance_id, fail_threshold, cooldown_sec
            )

        # 5. Priority Tier Routing Strategy
        elif strategy == "priority_tier":
            tier_var = config.get("priority_key", "user_tier")
            user_tier = str(
                context.get_variable(tier_var) 
                or (inputs.get("context", {}).get(tier_var) if isinstance(inputs.get("context"), dict) else None)
                or context.get_variable("user_role") 
                or "free"
            ).lower().strip()

            if user_tier in ("vip", "enterprise", "premium", "admin"):
                active_branch = "route_a"
                dispatched_reason = f"VIP Tier '{user_tier}' -> Route A (High Priority)"
            elif user_tier in ("staff", "pro", "standard", "manager"):
                active_branch = "route_b"
                dispatched_reason = f"Standard Tier '{user_tier}' -> Route B"
            else:
                active_branch = "route_c"
                dispatched_reason = f"Free/Guest Tier '{user_tier}' -> Route C"

        # Record context state
        context.set_variable("gateway_dispatched_route", active_branch)
        context.set_variable("gateway_strategy", strategy)
        context.log("info", f"Gateway dispatched to '{active_branch}': {dispatched_reason}")

        throttle_msg = config.get("throttle_message", "Rate limit exceeded.")
        payload_or_msg = throttle_msg if active_branch == "throttled" else query_input

        output_map = {
            "route_a": query_input if active_branch == "route_a" else None,
            "route_b": query_input if active_branch == "route_b" else None,
            "route_c": query_input if active_branch == "route_c" else None,
            "throttled": payload_or_msg if active_branch == "throttled" else None,
            "fallback": query_input if active_branch == "fallback" else None,
            "active_branch": active_branch,
            "metrics": {
                "strategy": strategy,
                "active_branch": active_branch,
                "reason": dispatched_reason,
                "throttle_triggered": throttle_triggered,
                "circuit_status": circuit_status,
                "timestamp": time.time()
            }
        }

        # If throttled, also set final_output fallback so user gets immediate response
        if active_branch == "throttled":
            context.set_variable("final_output", throttle_msg)

        return output_map

    async def execute_stream(
        self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        res = await self.execute(inputs, config, context)
        yield {"type": "result", "data": res}

    def _check_rate_limit(self, client_key: str, rps: float, burst: float) -> Tuple[bool, float]:
        """
        Token Bucket Rate Limiter per client key.
        """
        now = time.time()
        bucket = _GATEWAY_RATE_LIMITERS.get(client_key)
        if not bucket:
            bucket = {"tokens": burst - 1.0, "last_updated": now}
            _GATEWAY_RATE_LIMITERS[client_key] = bucket
            return True, bucket["tokens"]

        elapsed = now - bucket["last_updated"]
        bucket["tokens"] = min(burst, bucket["tokens"] + elapsed * rps)
        bucket["last_updated"] = now

        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True, bucket["tokens"]
        return False, bucket["tokens"]

    def _evaluate_circuit_breaker(
        self, node_id: str, threshold: int, cooldown_sec: float
    ) -> Tuple[str, str, str]:
        """
        Circuit Breaker state machine (CLOSED -> OPEN -> HALF_OPEN -> CLOSED).
        """
        now = time.time()
        cb = _GATEWAY_CIRCUIT_STATES.get(node_id)
        if not cb:
            cb = {"state": "CLOSED", "failure_count": 0, "last_state_change": now}
            _GATEWAY_CIRCUIT_STATES[node_id] = cb

        state = cb["state"]
        if state == "OPEN":
            if now - cb["last_state_change"] > cooldown_sec:
                cb["state"] = "HALF_OPEN"
                cb["last_state_change"] = now
                return "route_a", "HALF_OPEN", "Circuit cooldown expired. Attempting probe via Route A."
            else:
                rem_wait = round(cooldown_sec - (now - cb["last_state_change"]), 1)
                return "fallback", "OPEN", f"Circuit OPEN (Failures: {cb['failure_count']}). Cooldown {rem_wait}s remaining."

        return "route_a", state, f"Circuit {state}. Routing traffic normally via Route A."

    @classmethod
    def record_circuit_failure(cls, node_id: str = "default_gateway", threshold: int = 3):
        """Helper to trip circuit breaker upon downstream service errors."""
        now = time.time()
        cb = _GATEWAY_CIRCUIT_STATES.setdefault(node_id, {"state": "CLOSED", "failure_count": 0, "last_state_change": now})
        cb["failure_count"] += 1
        if cb["failure_count"] >= threshold:
            cb["state"] = "OPEN"
            cb["last_state_change"] = now

    @classmethod
    def reset_circuit(cls, node_id: str = "default_gateway"):
        """Helper to reset circuit breaker to closed state."""
        _GATEWAY_CIRCUIT_STATES[node_id] = {"state": "CLOSED", "failure_count": 0, "last_state_change": time.time()}

    @classmethod
    def reset_all_limiters(cls):
        """Helper for unit tests."""
        _GATEWAY_RATE_LIMITERS.clear()
        _GATEWAY_RR_COUNTERS.clear()
        _GATEWAY_CIRCUIT_STATES.clear()
