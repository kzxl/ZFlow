"""
ZFlow — Sovereign Chatbot Workflow Engine.
Provides visual orchestration and high-speed execution API for AI chatbots.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from nodes.base import NodeRegistry
import nodes  # Triggers automatic registration of all nodes into NodeRegistry

# Import modular API domain routers
from api import (
    workflows_router,
    execution_router,
    memory_router,
    knowledge_router,
    public_flows_router,
    system_router,
    settings_router,
    auth_router,
    telemetry_router
)

app = FastAPI(
    title="ZFlow — Sovereign Chatbot Workflow Engine",
    description="Node-based visual workflow & orchestration API for AI chatbots.",
    version="1.1.0"
)

# Enable CORS for Frontend dev server and local access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount domain routers
app.include_router(system_router)
app.include_router(workflows_router)
app.include_router(execution_router)
app.include_router(memory_router)
app.include_router(knowledge_router)
app.include_router(public_flows_router)
app.include_router(settings_router)
app.include_router(auth_router)
app.include_router(telemetry_router)

# Mount static build from web/dist if present for seamless single-server deployment
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "dist"))
if os.path.exists(DIST_DIR):
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
