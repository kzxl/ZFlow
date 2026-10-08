"""
ZFlow Session Memory Store.
Provides persistent SQLite and in-memory storage for multi-turn chatbot conversations.
Supports buffer windowing, token budgeting, and dialogue formatting.
"""
from typing import Dict, Any, List, Optional
import os
import sqlite3
import time
import json
import threading

class SessionMemoryStore:
    _instance: Optional['SessionMemoryStore'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if hasattr(self, "_initialized") and self._initialized:
            if db_path and db_path != self.db_path:
                self.db_path = db_path
                self._memory_cache = {}
                self._init_db()
            return
        
        self.db_path = db_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "chat_memory.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # In-memory session cache
        self._memory_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        self._init_db()
        self._initialized = True

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata_json TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON conversation_turns(session_id)")
            conn.commit()

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        use_sqlite: bool = True
    ) -> None:
        if not session_id or not content:
            return

        ts = time.time()
        msg_obj = {
            "role": role,
            "content": content,
            "timestamp": ts,
            "metadata": metadata or {}
        }

        # Update in-memory cache
        if session_id not in self._memory_cache:
            self._memory_cache[session_id] = []
        self._memory_cache[session_id].append(msg_obj)

        # Persist to SQLite
        if use_sqlite:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO conversation_turns (session_id, role, content, timestamp, metadata_json) VALUES (?, ?, ?, ?, ?)",
                        (session_id, role, content, ts, json.dumps(metadata or {}, ensure_ascii=False))
                    )
                    conn.commit()
            except Exception as e:
                print(f"[SessionMemoryStore] SQLite write error: {e}")

    def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
        use_sqlite: bool = True
    ) -> List[Dict[str, Any]]:
        if not session_id:
            return []

        if use_sqlite:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    if limit:
                        cursor.execute(
                            "SELECT role, content, timestamp, metadata_json FROM conversation_turns WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                            (session_id, limit)
                        )
                        rows = cursor.fetchall()
                        # Reverse to get chronological order
                        rows = list(reversed(rows))
                    else:
                        cursor.execute(
                            "SELECT role, content, timestamp, metadata_json FROM conversation_turns WHERE session_id = ? ORDER BY id ASC",
                            (session_id,)
                        )
                        rows = cursor.fetchall()

                    history = []
                    for r in rows:
                        meta = {}
                        if r["metadata_json"]:
                            try:
                                meta = json.loads(r["metadata_json"])
                            except Exception:
                                pass
                        history.append({
                            "role": r["role"],
                            "content": r["content"],
                            "timestamp": r["timestamp"],
                            "metadata": meta
                        })
                    return history
            except Exception as e:
                print(f"[SessionMemoryStore] SQLite read error: {e}")

        # Fallback to RAM cache
        cached = self._memory_cache.get(session_id, [])
        if limit and len(cached) > limit:
            return cached[-limit:]
        return list(cached)

    def clear_session(self, session_id: str) -> None:
        if session_id in self._memory_cache:
            del self._memory_cache[session_id]

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversation_turns WHERE session_id = ?", (session_id,))
                conn.commit()
        except Exception as e:
            print(f"[SessionMemoryStore] SQLite delete error: {e}")

    def clear_all(self) -> None:
        self._memory_cache.clear()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversation_turns")
                conn.commit()
        except Exception as e:
            print(f"[SessionMemoryStore] SQLite clear all error: {e}")

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = {}
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_id, COUNT(*) as turn_count, MAX(timestamp) as last_updated
                    FROM conversation_turns
                    GROUP BY session_id
                    ORDER BY last_updated DESC
                """)
                for r in cursor.fetchall():
                    sess_id = r["session_id"]
                    cursor.execute(
                        "SELECT role, content FROM conversation_turns WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                        (sess_id,)
                    )
                    last_turn = cursor.fetchone()
                    sessions[sess_id] = {
                        "session_id": sess_id,
                        "turn_count": r["turn_count"],
                        "last_updated": r["last_updated"],
                        "last_message": last_turn["content"][:120] if last_turn else "",
                        "last_role": last_turn["role"] if last_turn else "user"
                    }
        except Exception as e:
            print(f"[SessionMemoryStore] SQLite list sessions error: {e}")

        # Merge RAM cached sessions
        for s_id, msgs in self._memory_cache.items():
            if s_id not in sessions and msgs:
                sessions[s_id] = {
                    "session_id": s_id,
                    "turn_count": len(msgs),
                    "last_updated": msgs[-1].get("timestamp", time.time()),
                    "last_message": msgs[-1].get("content", "")[:120],
                    "last_role": msgs[-1].get("role", "user")
                }

        return sorted(list(sessions.values()), key=lambda x: x.get("last_updated", 0), reverse=True)

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        history = self.get_history(session_id)
        user_turns = sum(1 for m in history if m.get("role") == "user")
        bot_turns = sum(1 for m in history if m.get("role") == "assistant")
        total_chars = sum(len(m.get("content", "")) for m in history)
        return {
            "session_id": session_id,
            "turn_count": len(history),
            "user_turns": user_turns,
            "assistant_turns": bot_turns,
            "total_chars": total_chars,
            "estimated_tokens": total_chars // 4,
            "last_updated": history[-1]["timestamp"] if history else time.time()
        }

    @staticmethod
    def format_history_string(
        history: List[Dict[str, Any]],
        human_prefix: str = "User",
        ai_prefix: str = "Assistant"
    ) -> str:
        lines = []
        for msg in history:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "").strip()
            prefix = human_prefix if role in ("user", "human") else ai_prefix
            lines.append(f"{prefix}: {content}")
        return "\n".join(lines)


# Global singleton instance
memory_store = SessionMemoryStore()
