"""
Conversation Memory Router.
Manages multi-turn session persistence, history retrieval, stats, and markdown exports.
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
import time

from engine.memory_store import memory_store

router = APIRouter(tags=["Memory"])


@router.get("/api/memory/sessions")
async def list_memory_sessions():
    """Returns list of all conversation sessions stored in SQLite with stats and message previews."""
    return {"sessions": memory_store.list_sessions()}


@router.get("/api/memory/sessions/{session_id}")
async def get_session_history(session_id: str):
    """Retrieves chronological dialogue history and statistics for a specific session."""
    history = memory_store.get_history(session_id)
    stats = memory_store.get_session_stats(session_id)
    return {
        "session_id": session_id,
        "stats": stats,
        "history": history
    }


@router.delete("/api/memory/sessions/{session_id}")
async def clear_session_memory(session_id: str):
    """Clears all persistent conversation turns for a session from SQLite."""
    memory_store.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


@router.post("/api/memory/sessions/{session_id}/clear")
async def clear_session_memory_post(session_id: str):
    """Alternative POST endpoint for clearing session memory."""
    memory_store.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


@router.get("/api/memory/sessions/{session_id}/stats")
async def get_session_stats_endpoint(session_id: str):
    """Retrieves turn counts, estimated tokens, and message breakdown for a session."""
    return memory_store.get_session_stats(session_id)


@router.get("/api/memory/sessions/{session_id}/export")
async def export_session_memory(session_id: str, format: str = "json"):
    """
    Exports full conversation history for a given session.
    Supported format: 'json' or 'markdown' / 'md'.
    """
    history = memory_store.get_history(session_id)
    stats = memory_store.get_session_stats(session_id)

    if format.lower() in ("markdown", "md"):
        lines = [
            f"# ZFlow Conversation Transcript - {session_id}",
            f"- **Session ID:** `{session_id}`",
            f"- **Total Turns:** {len(history)}",
            f"- **User Turns:** {stats.get('user_turns', 0)}",
            f"- **Assistant Turns:** {stats.get('assistant_turns', 0)}",
            f"- **Exported At:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ]
        for turn in history:
            role_icon = "👤" if turn.get("role") == "user" else "🤖"
            role_name = "User" if turn.get("role") == "user" else "Assistant"
            timestamp_str = time.strftime('%H:%M:%S', time.localtime(turn.get("timestamp", time.time())))
            lines.append(f"### {role_icon} {role_name} ({timestamp_str})")
            lines.append(turn.get("content", ""))
            lines.append("")
        return PlainTextResponse("\n".join(lines), media_type="text/markdown")

    return {
        "session_id": session_id,
        "exported_at": time.time(),
        "stats": stats,
        "history": history
    }
