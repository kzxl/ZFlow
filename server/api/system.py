"""
System Utilities & Health Router.
Provides health checks, node definitions catalog, micro-benchmarks, and prompt enchanters.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
import time
import os

from nodes.base import NodeRegistry
from engine.graph import WorkflowGraph
from engine.context import ExecutionContext
from engine.runner import WorkflowRunner
from engine.memory_store import memory_store

router = APIRouter(tags=["System"])


@router.get("/health")
async def health_check():
    """Returns engine health, app name, version, and registered node counts."""
    return {
        "status": "ok",
        "app": "ZFlow",
        "registered_nodes": len(NodeRegistry.list_all_metadata()),
        "version": "1.1.0"
    }


@router.get("/api/nodes")
async def get_node_definitions():
    """
    Returns list of all registered node types, their inputs/outputs ports and configuration schema.
    Used by the Frontend canvas to populate the node sidebar palette.
    """
    return {"nodes": NodeRegistry.list_all_metadata()}


@router.get("/api/system/benchmark")
async def run_system_benchmark():
    """
    Executes a high-speed micro-benchmark measuring:
    1. SQLite memory insertion & retrieval latency (ms)
    2. Workflow DAG topological resolution & engine runner overhead (ms)
    3. Memory statistics
    """
    # 1. SQLite Memory latency
    bench_session = f"bench_temp_{int(time.time() * 1000)}"
    t_start_write = time.perf_counter()
    for i in range(5):
        memory_store.append_message(bench_session, "user", f"Bench query {i}")
        memory_store.append_message(bench_session, "assistant", f"Bench answer {i}")
    write_latency_ms = round(((time.perf_counter() - t_start_write) / 10) * 1000, 3)

    t_start_read = time.perf_counter()
    _ = memory_store.get_history(bench_session, limit=10)
    read_latency_ms = round((time.perf_counter() - t_start_read) * 1000, 3)

    # Clean up benchmark session
    memory_store.clear_session(bench_session)

    # 2. Pure Engine DAG Overhead
    sample_flow = {
        "id": "bench_flow",
        "nodes": [
            {"id": "node_input", "type": "input", "config": {}},
            {"id": "node_prompt", "type": "prompt", "config": {"template": "Echo: {input}"}},
            {"id": "node_output", "type": "output", "config": {"output_key": "reply"}}
        ],
        "edges": [
            {"id": "e1", "source": "node_input", "target": "node_prompt"},
            {"id": "e2", "source": "node_prompt", "target": "node_output"}
        ]
    }
    t_start_dag = time.perf_counter()
    graph = WorkflowGraph.from_dict(sample_flow)
    runner = WorkflowRunner()
    context = ExecutionContext(session_id="bench_ctx", initial_variables={"input": "ZFlow benchmark"})
    _ = await runner.run(graph, context)
    dag_overhead_ms = round((time.perf_counter() - t_start_dag) * 1000, 3)

    sessions = memory_store.list_sessions()
    total_turns = sum(s.get("turn_count", 0) for s in sessions)

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "benchmarks": {
            "sqlite_write_latency_per_turn_ms": write_latency_ms,
            "sqlite_read_latency_ms": read_latency_ms,
            "pure_dag_overhead_ms": dag_overhead_ms,
            "engine_throughput_estimate_qps": round(1000.0 / max(dag_overhead_ms, 0.1), 1)
        },
        "storage": {
            "total_saved_sessions": len(sessions),
            "total_saved_turns": total_turns,
            "database_file": os.path.basename(memory_store.db_path)
        }
    }


class EnchantPromptRequest(BaseModel):
    prompt: str = Field(..., description="Base concept or prompt")
    enchant_level: Optional[str] = "vivid"
    style: Optional[str] = "cinematic"
    lighting: Optional[str] = "dramatic"
    camera: Optional[str] = "none"
    atmosphere: Optional[str] = "none"
    artist: Optional[str] = "none"
    extra_boosters: Optional[str] = ""
    enable_subject_detailing: Optional[bool] = True


@router.post("/api/enchant-prompt")
async def api_enchant_prompt(payload: EnchantPromptRequest):
    """Enchants and expands a simple concept into an ultra-detailed diffusion prompt."""
    from nodes.prompt_styler_node import enchant_prompt
    result = enchant_prompt(
        base_prompt=payload.prompt,
        enchant_level=payload.enchant_level or "vivid",
        style=payload.style or "cinematic",
        lighting=payload.lighting or "dramatic",
        camera=payload.camera or "none",
        atmosphere=payload.atmosphere or "none",
        artist=payload.artist or "none",
        extra_boosters=payload.extra_boosters or "",
        enable_subject_detailing=payload.enable_subject_detailing if payload.enable_subject_detailing is not None else True
    )
    return result


class ComfyUiTestRequest(BaseModel):
    base_url: str = Field(default="http://192.168.10.7:8188", description="ComfyUI server URL")


@router.post("/api/system/comfyui/test")
async def test_comfyui_connection(req: ComfyUiTestRequest):
    """
    Pings the user's ComfyUI server, checks queue, and retrieves active model/workflow info.
    """
    base_url = req.base_url.rstrip("/")
    import httpx
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            # 1. Check /queue
            q_resp = await client.get(f"{base_url}/queue")
            q_data = q_resp.json() if q_resp.status_code == 200 else {}

            # 2. Check /history to get active workflow models
            h_resp = await client.get(f"{base_url}/history")
            h_data = h_resp.json() if h_resp.status_code == 200 else {}
            active_models = []
            if h_data:
                latest_id = list(h_data.keys())[-1]
                prompt_tuple = h_data[latest_id].get("prompt", [])
                if len(prompt_tuple) > 2:
                    wf = prompt_tuple[2]
                    for nid, node in wf.items():
                        inputs = node.get("inputs", {})
                        if "unet_name" in inputs:
                            active_models.append(f"UNET: {inputs['unet_name']}")
                        elif "ckpt_name" in inputs:
                            active_models.append(f"Checkpoint: {inputs['ckpt_name']}")
                        elif "vae_name" in inputs:
                            active_models.append(f"VAE: {inputs['vae_name']}")

            return {
                "status": "connected",
                "base_url": base_url,
                "queue_running": len(q_data.get("queue_running", [])),
                "queue_pending": len(q_data.get("queue_pending", [])),
                "active_models": list(set(active_models)),
                "history_count": len(h_data),
                "message": "Kết nối thành công tới ComfyUI Server!"
            }
    except Exception as e:
        return {
            "status": "error",
            "base_url": base_url,
            "error": str(e),
            "message": f"Không thể kết nối tới ComfyUI: {e}"
        }

