"""Opt-in CMS module — a content manager an org self-publishes to.

fi-INDEPENDENT: plain FastAPI + pydantic + a swappable store. It does NOT import
fi_runner, so it mounts (and tests) without the agent stack. Enable it by adding
``cms`` to the ``APP_MODULES`` env var (see ``app.modules``); the router is then
included alongside the always-on chat router.
"""
from __future__ import annotations

from .routes import cms_router

__all__ = ["cms_router"]
