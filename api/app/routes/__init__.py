"""Route sub-package — re-exports the APIRouters for include_router in app.py."""
from .chat import router as chat_router

__all__ = ["chat_router"]
