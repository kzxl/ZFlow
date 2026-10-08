"""
System Settings API Router.
Provides endpoints for global configuration, API keys, active workflow binding, and engine tuning.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import os

from engine.settings_manager import settings_manager
from engine.cache_store import cache_store

router = APIRouter(tags=["Settings"])


class SettingsUpdatePayload(BaseModel):
    settings: Dict[str, Any] = Field(..., description="Key-value dictionary of settings to update")


class SetActiveFlowPayload(BaseModel):
    flow_id: str = Field(..., description="ID of the workflow to mark as active")


def mask_secret(val: str) -> str:
    """Masks secret key to display only prefix and suffix."""
    if not val or len(val) < 8:
        return "••••••••" if val else ""
    return f"{val[:4]}••••••••{val[-4:]}"


@router.get("/api/settings")
async def get_system_settings(raw_keys: bool = False):
    """
    Returns global system settings.
    If raw_keys is False, masks sensitive API keys for safe UI display.
    """
    all_s = settings_manager.get_all()
    if not raw_keys:
        safe_copy = all_s.copy()
        for k in ["openai_api_key", "gemini_api_key", "deepseek_api_key", "claude_api_key", "groq_api_key"]:
            if safe_copy.get(k):
                safe_copy[k] = mask_secret(safe_copy[k])
        return {"settings": safe_copy, "is_masked": True}
    return {"settings": all_s, "is_masked": False}


@router.post("/api/settings")
async def update_system_settings(payload: SettingsUpdatePayload):
    """Updates one or more global system settings."""
    filtered = {}
    for k, v in payload.settings.items():
        # Skip masked placeholders sent back from UI
        if isinstance(v, str) and "••••••••" in v:
            continue
        filtered[k] = v

    updated = settings_manager.update(filtered)
    return {"status": "saved", "updated_keys": list(filtered.keys())}


@router.post("/api/settings/active-flow")
async def set_active_workflow(payload: SetActiveFlowPayload):
    """
    Sets the active workflow. External API callers using /api/v1/flows/active/run
    will immediately execute this workflow.
    """
    settings_manager.set("active_flow_id", payload.flow_id)
    return {
        "status": "success",
        "active_flow_id": payload.flow_id,
        "message": f"Workflow '{payload.flow_id}' is now designated as the system Active Flow."
    }


@router.post("/api/settings/clear-cache")
async def clear_semantic_cache():
    """Clears all cached records from the semantic cache database."""
    with cache_store._get_conn() as conn:
        conn.execute("DELETE FROM semantic_cache")
        conn.commit()
    return {"status": "cleared", "message": "Semantic cache store has been completely wiped."}
