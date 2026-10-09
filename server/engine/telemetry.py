"""
ZFlow In-Memory Telemetry & Real-Time Traffic Observability Engine.
Collects sub-microsecond atomic concurrency counters, per-node in-flight traffic,
sliding window throughput (RPS), and latency heatmaps with ZERO disk/database overhead.
"""
import time
import asyncio
from collections import deque
from typing import Dict, Any, List, Optional
import threading

class NodeTelemetry:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.in_flight: int = 0
        self.total_completed: int = 0
        self.total_errors: int = 0
        self.avg_duration_ms: float = 0.0
        self.recent_durations: deque = deque(maxlen=50)

    def record_start(self):
        self.in_flight += 1

    def record_end(self, duration_ms: float, is_error: bool = False):
        self.in_flight = max(0, self.in_flight - 1)
        if is_error:
            self.total_errors += 1
        else:
            self.total_completed += 1
            self.recent_durations.append(duration_ms)
            # Exponentially Weighted Moving Average (alpha=0.2)
            if self.avg_duration_ms == 0.0:
                self.avg_duration_ms = duration_ms
            else:
                self.avg_duration_ms = round(0.2 * duration_ms + 0.8 * self.avg_duration_ms, 2)

    def get_p95_duration(self) -> float:
        if not self.recent_durations:
            return self.avg_duration_ms
        sorted_d = sorted(self.recent_durations)
        idx = int(len(sorted_d) * 0.95)
        return round(sorted_d[min(idx, len(sorted_d) - 1)], 2)

    def get_heat_status(self) -> str:
        """Calculates latency & congestion heat state for canvas visualization."""
        if self.total_errors > 0 and self.total_completed == 0:
            return "error"
        if self.in_flight == 0:
            return "idle"
        if self.in_flight >= 8 or self.avg_duration_ms >= 3000.0:
            return "congested" # Red alert (bottleneck)
        if self.in_flight >= 3 or self.avg_duration_ms >= 800.0:
            return "busy"      # Yellow warning
        return "normal"        # Green healthy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "in_flight": self.in_flight,
            "total_completed": self.total_completed,
            "total_errors": self.total_errors,
            "avg_duration_ms": self.avg_duration_ms,
            "p95_duration_ms": self.get_p95_duration(),
            "heat_status": self.get_heat_status()
        }


class TelemetryManager:
    """
    Singleton in-memory telemetry aggregator.
    Maintains real-time workflow traffic counters and broadcasts snapshots to web clients.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self.total_in_flight: int = 0
        self.total_completed_requests: int = 0
        self.total_failed_requests: int = 0
        self.workflow_in_flight: Dict[str, int] = {}
        self.nodes: Dict[str, NodeTelemetry] = {}
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        self.recent_request_timestamps: deque = deque(maxlen=2000)

    def on_workflow_start(self, flow_id: str, session_id: str, user_id: str = "guest") -> str:
        with self._lock:
            self.total_in_flight += 1
            self.workflow_in_flight[flow_id] = self.workflow_in_flight.get(flow_id, 0) + 1
            now = time.time()
            self.active_requests[session_id] = {
                "session_id": session_id,
                "flow_id": flow_id,
                "user_id": user_id,
                "current_node_id": "",
                "start_time": now,
                "nodes_traversed": []
            }
        return session_id

    def on_node_start(self, flow_id: str, node_id: str, session_id: str):
        with self._lock:
            if node_id not in self.nodes:
                self.nodes[node_id] = NodeTelemetry(node_id)
            self.nodes[node_id].record_start()
            if session_id in self.active_requests:
                self.active_requests[session_id]["current_node_id"] = node_id
                self.active_requests[session_id]["nodes_traversed"].append(node_id)

    def on_node_end(self, flow_id: str, node_id: str, session_id: str, duration_ms: float, is_error: bool = False):
        with self._lock:
            if node_id in self.nodes:
                self.nodes[node_id].record_end(duration_ms, is_error)

    def on_workflow_end(self, flow_id: str, session_id: str, is_error: bool = False):
        with self._lock:
            self.total_in_flight = max(0, self.total_in_flight - 1)
            if flow_id in self.workflow_in_flight:
                self.workflow_in_flight[flow_id] = max(0, self.workflow_in_flight[flow_id] - 1)

            now = time.time()
            self.recent_request_timestamps.append(now)
            if is_error:
                self.total_failed_requests += 1
            else:
                self.total_completed_requests += 1

            self.active_requests.pop(session_id, None)

    def get_current_rps(self) -> float:
        """Calculates requests per second over the last 5-second sliding window."""
        now = time.time()
        window_start = now - 5.0
        with self._lock:
            recent_count = sum(1 for ts in self.recent_request_timestamps if ts >= window_start)
        return round(recent_count / 5.0, 2)

    def get_snapshot(self, flow_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns instantaneous snapshot of concurrency, throughput, and node heat states."""
        now = time.time()
        with self._lock:
            node_data = {nid: n.to_dict() for nid, n in self.nodes.items()}
            current_active = []
            for s_id, req in list(self.active_requests.items()):
                if not flow_id or req.get("flow_id") == flow_id:
                    current_active.append({
                        "session_id": s_id,
                        "flow_id": req["flow_id"],
                        "user_id": req["user_id"],
                        "current_node_id": req["current_node_id"],
                        "elapsed_seconds": round(now - req["start_time"], 2)
                    })

            # Calculate global P95 duration across all nodes
            all_durations = []
            for n in self.nodes.values():
                all_durations.extend(n.recent_durations)
            p95_global = 0.0
            if all_durations:
                sorted_all = sorted(all_durations)
                p95_global = round(sorted_all[min(int(len(sorted_all) * 0.95), len(sorted_all) - 1)], 2)

            total_reqs = self.total_completed_requests + self.total_failed_requests
            err_rate = round((self.total_failed_requests / total_reqs * 100), 2) if total_reqs > 0 else 0.0

            return {
                "timestamp": now,
                "total_in_flight": self.total_in_flight,
                "workflow_in_flight": self.workflow_in_flight.get(flow_id, 0) if flow_id else self.total_in_flight,
                "current_rps": self.get_current_rps(),
                "p95_latency_ms": p95_global,
                "error_rate_pct": err_rate,
                "total_completed": self.total_completed_requests,
                "total_failed": self.total_failed_requests,
                "nodes": node_data,
                "active_requests_count": len(current_active),
                "active_requests": current_active[:20]  # top 20 active for preview
            }

    def reset(self):
        with self._lock:
            self.total_in_flight = 0
            self.total_completed_requests = 0
            self.total_failed_requests = 0
            self.workflow_in_flight.clear()
            self.nodes.clear()
            self.active_requests.clear()
            self.recent_request_timestamps.clear()


# Global Singleton instance
telemetry_manager = TelemetryManager()
