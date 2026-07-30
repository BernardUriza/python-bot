"""Opt-in CMS module — a content manager an org self-publishes to.

fi-INDEPENDENT: plain FastAPI + pydantic + a swappable store. It does NOT import
fi_runner, so it mounts (and tests) without the agent stack. Enable it by adding
``cms`` to the ``APP_MODULES`` env var (see ``app.modules``); the router is then
included alongside the always-on chat router.

``cms_router`` resolves lazily (PEP 562) so importing the pure-pydantic halves —
``app.cms.models``, ``app.cms.store`` — costs nothing but pydantic. Eagerly importing the router here dragged ``app.auth`` (and with it
slowapi and the whole web stack) into every consumer of the models: a seed
validator or a content script then died with ModuleNotFoundError outside the API
environment, for code that never needed a web framework.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .routes import cms_router

__all__ = ["cms_router"]


def __getattr__(name: str):
    if name == "cms_router":
        from .routes import cms_router

        return cms_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
