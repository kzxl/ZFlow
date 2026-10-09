"""
ZFlow Telemetry & Real-Time Traffic Observability API Router.
Provides live SSE streams, instant snapshots, and active requests inspection for Visual Heatmaps.
"""
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
import json
import asyncio

from engine.telemetry import telemetry_manager

router = APIRouter(tags=["Telemetry & Observability"])


@router.get("/api/v1/telemetry/snapshot")
async def get_telemetry_snapshot(
    flow_id: Optional[str] = Query(None, description="Optional target workflow ID filter")
):
    """
    Returns an instantaneous snapshot of current concurrency, throughput,
    and per-node in-flight traffic & heat states.
    """
    return telemetry_manager.get_snapshot(flow_id)


@router.get("/api/v1/telemetry/active-requests")
async def get_active_requests(
    flow_id: Optional[str] = Query(None, description="Optional target workflow ID filter")
):
    """
    Returns the list of currently executing in-flight requests across nodes
    for the Live Request Inspector drawer.
    """
    snapshot = telemetry_manager.get_snapshot(flow_id)
    return {
        "count": snapshot["active_requests_count"],
        "active_requests": snapshot["active_requests"]
    }


@router.get("/api/v1/telemetry/live")
async def live_telemetry_stream(
    flow_id: Optional[str] = Query(None, description="Optional workflow ID to filter"),
    interval_ms: int = Query(350, ge=100, le=2000, description="Broadcast interval in milliseconds")
):
    """
    Real-time SSE stream pushing live telemetry frames every ~350ms to the Frontend canvas.
    Powers the visual glowing badges, animated traffic edges, and congestion heatmap.
    """
    interval_sec = interval_ms / 1000.0

    async def event_generator():
        try:
            while True:
                snapshot = telemetry_manager.get_snapshot(flow_id)
                data_str = json.dumps(snapshot, ensure_ascii=False)
                yield f"event: telemetry\ndata: {data_str}\n\n"
                await asyncio.sleep(interval_sec)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/api/v1/telemetry/reset")
async def reset_telemetry():
    """Resets all in-memory telemetry counters."""
    telemetry_manager.reset()
    return {"status": "success", "message": "Telemetry metrics reset."}
