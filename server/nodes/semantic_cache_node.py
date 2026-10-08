"""
Multi-Tier Semantic & Exact Cache Node.
Provides ultra-fast (< 0.1ms) response memoization using two-tier retrieval:
1. Tier 1: Exact SHA256 Hash Matching
2. Tier 2: Semantic Token Overlap & Soft Jaccard Similarity Matching (Zero Token Cost)
Supports TTL expiration and automatic write-through caching.
"""
import time
from typing import Dict, Any, List, Optional
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext
from engine.cache_store import cache_store, CacheStore, normalize_query, compute_token_similarity


@NodeRegistry.register
class SemanticCacheNode(BaseNode):
    node_type = "semantic_cache"
    name = "Semantic & Exact Cache"
    category = "tool"
    description = "Kiểm tra cache câu hỏi tương tự theo ngữ nghĩa (< 0.1ms). Hit cache -> Trả lời ngay không tốn token LLM; Miss -> Cho flow đi tiếp."
    icon = "Database"

    inputs = [
        PortDef(name="query", data_type="string", label="Incoming Query", required=True),
        PortDef(name="response_to_cache", data_type="string", label="Response to Write (Optional)", required=False)
    ]
    outputs = [
        PortDef(name="cache_hit", data_type="string", label="⚡ Cache Hit (Cached Answer)"),
        PortDef(name="cache_miss", data_type="string", label="🔍 Cache Miss (Query Forward)"),
        PortDef(name="active_branch", data_type="string", label="Active Branch"),
        PortDef(name="is_hit", data_type="boolean", label="Is Cache Hit"),
        PortDef(name="cached_response", data_type="string", label="Cached Response Content"),
        PortDef(name="similarity_score", data_type="number", label="Match Similarity (0-1)"),
        PortDef(name="latency_ms", data_type="number", label="Cache Lookup Latency (ms)")
    ]

    config_schema = {
        "mode": {
            "type": "select",
            "label": "Cache Mode",
            "options": ["read_or_write", "read_only", "write_only"],
            "default": "read_or_write"
        },
        "similarity_threshold": {
            "type": "number",
            "label": "Semantic Match Threshold (0.70 - 1.0)",
            "default": 0.85,
            "min": 0.70,
            "max": 1.0,
            "step": 0.05
        },
        "ttl_seconds": {
            "type": "number",
            "label": "Cache Expiration TTL (Seconds)",
            "default": 86400,
            "min": 60,
            "max": 2592000,
            "step": 3600
        }
    }

    async def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        query = str(
            inputs.get("query")
            or inputs.get("input")
            or context.get_variable("query")
            or context.get_variable("input", "")
        ).strip()

        resp_to_write = inputs.get("response_to_cache")
        mode = config.get("mode", "read_or_write")
        threshold = float(config.get("similarity_threshold", 0.85))
        ttl = int(config.get("ttl_seconds", 86400))

        # Action: Write if in write_only mode or response_to_cache port is provided
        if mode == "write_only" or (mode == "read_or_write" and resp_to_write):
            if not resp_to_write and mode == "write_only":
                resp_to_write = context.get_variable("reply") or context.get_variable("final_output")
            if resp_to_write:
                cache_store.set(query, str(resp_to_write), ttl_seconds=ttl)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 3)
                context.log("info", f"Semantic Cache wrote entry for query: '{query[:40]}' (TTL: {ttl}s)")
                return {
                    "active_branch": "cache_miss",
                    "is_hit": False,
                    "cached_response": str(resp_to_write),
                    "cache_hit": "",
                    "cache_miss": query,
                    "similarity_score": 1.0,
                    "latency_ms": latency_ms
                }

        # Action: Read lookup
        cached_item = cache_store.get(query, similarity_threshold=threshold)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 3)

        if cached_item:
            cached_resp, sim_score, match_type = cached_item
            context.set_variable("cache_hit", True)
            context.set_variable("cached_response", cached_resp)
            context.set_variable("reply", cached_resp)
            context.set_variable("final_output", cached_resp)
            context.log("info", f"Semantic Cache HIT ({match_type}, score: {sim_score}) in {latency_ms}ms!")
            return {
                "active_branch": "cache_hit",
                "is_hit": True,
                "cached_response": cached_resp,
                "cache_hit": cached_resp,
                "cache_miss": "",
                "similarity_score": sim_score,
                "latency_ms": latency_ms
            }

        context.set_variable("cache_hit", False)
        context.set_variable("cache_miss_query", query)
        context.log("info", f"Semantic Cache MISS for query: '{query[:40]}'")
        return {
            "active_branch": "cache_miss",
            "is_hit": False,
            "cached_response": "",
            "cache_hit": "",
            "cache_miss": query,
            "similarity_score": 0.0,
            "latency_ms": latency_ms
        }
