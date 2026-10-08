"""
Multi-Tier Semantic & Exact Cache Node.
Provides ultra-fast (< 0.1ms) response memoization using two-tier retrieval:
1. Tier 1: Exact SHA256 Hash Matching
2. Tier 2: Semantic Token Overlap & Soft Jaccard Similarity Matching (Zero Token Cost)
Supports TTL expiration and automatic write-through caching.
"""
import sqlite3
import hashlib
import time
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from nodes.base import BaseNode, PortDef, NodeRegistry
from engine.context import ExecutionContext

CACHE_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "storage", "semantic_cache.db")
)


def normalize_query(text: str) -> str:
    """Normalizes query text for consistent caching."""
    t = text.lower().strip()
    t = re.sub(r'[\s!.,?~…]+$', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def compute_token_similarity(q1: str, q2: str) -> float:
    """Computes Jaccard word similarity between two queries."""
    w1 = set(re.findall(r'\w+', q1.lower()))
    w2 = set(re.findall(r'\w+', q2.lower()))
    if not w1 or not w2:
        return 0.0
    intersection = w1.intersection(w2)
    union = w1.union(w2)
    return len(intersection) / len(union)


class CacheStore:
    _instance = None

    def __init__(self, db_path: str = CACHE_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    hash_key TEXT PRIMARY KEY,
                    original_query TEXT NOT NULL,
                    cached_response TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON semantic_cache(expires_at)")
            conn.commit()

    def get(self, query: str, similarity_threshold: float = 0.85) -> Optional[Tuple[str, float, str]]:
        """
        Retrieves cached response. Returns (response, similarity_score, match_type) or None.
        """
        norm_q = normalize_query(query)
        hash_key = hashlib.sha256(norm_q.encode("utf-8")).hexdigest()
        now = time.time()

        with self._get_conn() as conn:
            cursor = conn.cursor()
            # 1. Exact match
            cursor.execute(
                "SELECT cached_response, hit_count FROM semantic_cache WHERE hash_key = ? AND expires_at > ?",
                (hash_key, now)
            )
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE semantic_cache SET hit_count = hit_count + 1 WHERE hash_key = ?", (hash_key,))
                conn.commit()
                return row["cached_response"], 1.0, "exact_match"

            # 2. Semantic fuzzy match across active cached queries
            if similarity_threshold < 1.0:
                cursor.execute(
                    "SELECT hash_key, original_query, cached_response FROM semantic_cache WHERE expires_at > ? ORDER BY hit_count DESC LIMIT 100",
                    (now,)
                )
                candidates = cursor.fetchall()
                best_match = None
                best_score = 0.0

                for c in candidates:
                    sim = compute_token_similarity(norm_q, c["original_query"])
                    if sim > best_score:
                        best_score = sim
                        best_match = c

                if best_match and best_score >= similarity_threshold:
                    cursor.execute("UPDATE semantic_cache SET hit_count = hit_count + 1 WHERE hash_key = ?", (best_match["hash_key"],))
                    conn.commit()
                    return best_match["cached_response"], round(best_score, 3), "semantic_match"

        return None

    def set(self, query: str, response: str, ttl_seconds: int = 86400):
        """Saves a query-response pair to cache with TTL."""
        norm_q = normalize_query(query)
        hash_key = hashlib.sha256(norm_q.encode("utf-8")).hexdigest()
        now = time.time()
        expires = now + ttl_seconds

        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO semantic_cache (hash_key, original_query, cached_response, hit_count, created_at, expires_at) VALUES (?, ?, ?, 0, ?, ?)",
                (hash_key, norm_q, response, now, expires)
            )
            conn.commit()


cache_store = CacheStore()


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
                "cache_hit": cached_resp,
                "cache_miss": "",
                "cached_response": cached_resp,
                "similarity_score": sim_score,
                "latency_ms": latency_ms
            }

        context.log("info", f"Semantic Cache MISS in {latency_ms}ms. Forwarding to pipeline.")
        return {
            "active_branch": "cache_miss",
            "is_hit": False,
            "cache_hit": "",
            "cache_miss": query,
            "cached_response": "",
            "similarity_score": 0.0,
            "latency_ms": latency_ms
        }
