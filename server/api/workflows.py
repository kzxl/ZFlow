"""
Workflow Management Router.
Handles workflow persistence, listing, creation, and deletion in storage.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import os
import glob
import json
import re

router = APIRouter(tags=["Workflows"])

STORAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "storage")
)
os.makedirs(STORAGE_DIR, exist_ok=True)


class WorkflowPayload(BaseModel):
    id: Optional[str] = "custom_flow"
    name: Optional[str] = "Untitled Flow"
    description: Optional[str] = ""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)


def load_flow_data(flow_id: str) -> Dict[str, Any]:
    """Helper to locate and parse workflow JSON from storage."""
    target = os.path.join(STORAGE_DIR, f"{flow_id}.json")
    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)

    # Check if any saved JSON file has matching internal id
    for fp in glob.glob(os.path.join(STORAGE_DIR, "*.json")):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
                if d.get("id") == flow_id:
                    return d
        except Exception:
            continue

    # Fallback to default_flow.json
    target = os.path.join(STORAGE_DIR, "default_flow.json")
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail=f"Workflow '{flow_id}' not found.")

    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/api/workflows")
async def list_workflows():
    """Lists saved workflows in the local storage directory."""
    workflows = []
    seen_ids = set()
    for filepath in glob.glob(os.path.join(STORAGE_DIR, "*.json")):
        file_stem = os.path.splitext(os.path.basename(filepath))[0]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                flow_id = data.get("id") or file_stem
                if flow_id in seen_ids:
                    flow_id = file_stem
                seen_ids.add(flow_id)
                workflows.append({
                    "id": flow_id,
                    "file_stem": file_stem,
                    "name": data.get("name", file_stem.replace("_", " ").title()),
                    "description": data.get("description", ""),
                    "node_count": len(data.get("nodes", [])),
                    "edge_count": len(data.get("edges", []))
                })
        except Exception:
            continue
    return {"workflows": workflows}


@router.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Retrieves full workflow JSON definition."""
    return load_flow_data(workflow_id)


def save_flow_data(flow_id: str, data: Dict[str, Any]) -> str:
    """Helper to persist a workflow definition JSON to local storage."""
    raw_id = flow_id or data.get("id") or data.get("name") or "custom_flow"
    wf_id = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_id.strip()).lower()
    wf_id = re.sub(r'_+', '_', wf_id).strip('_') or "custom_flow"

    save_obj = dict(data)
    save_obj["id"] = wf_id
    if not save_obj.get("name"):
        save_obj["name"] = wf_id.replace("_", " ").title()

    target = os.path.join(STORAGE_DIR, f"{wf_id}.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(save_obj, f, indent=2, ensure_ascii=False)
    return wf_id


@router.post("/api/workflows")
async def save_workflow(payload: WorkflowPayload):
    """Saves or updates a workflow JSON definition."""
    data = payload.model_dump()
    wf_id = save_flow_data(payload.id or payload.name or "custom_flow", data)
    return {"status": "saved", "id": wf_id, "name": data.get("name", wf_id)}


@router.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Deletes a saved workflow from storage (protects default_flow.json)."""
    if workflow_id in ["default_flow"]:
        raise HTTPException(status_code=400, detail="Cannot delete default system starter template.")
    target = os.path.join(STORAGE_DIR, f"{workflow_id}.json")
    if os.path.exists(target):
        os.remove(target)
        return {"status": "deleted", "id": workflow_id}
    raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
