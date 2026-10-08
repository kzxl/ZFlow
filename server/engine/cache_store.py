"""
ZFlow Sovereign Cache Store.
Provides multi-tier high-speed response caching:
1. Tier 1: Exact SHA256 Hash Matching (< 0.1ms)
2. Tier 2: Semantic Token Overlap & Soft Jaccard Similarity (Zero token cost)
Supports TTL expiration, hit-counter tracking, and SQLite persistence.
"""
import sqlite3
import hashlib
import time
import os
import re
from typing import Dict, Any, List, Optional, Tuple

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
