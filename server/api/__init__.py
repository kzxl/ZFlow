"""
ZFlow API Routers Package.
Organizes REST and SSE endpoints into modular domain routers.
"""
from .workflows import router as workflows_router
from .execution import router as execution_router
from .memory import router as memory_router
from .knowledge import router as knowledge_router
from .public_flows import router as public_flows_router
from .system import router as system_router
from .settings import router as settings_router

__all__ = [
    "workflows_router",
    "execution_router",
    "memory_router",
    "knowledge_router",
    "public_flows_router",
    "system_router",
    "settings_router"
]
