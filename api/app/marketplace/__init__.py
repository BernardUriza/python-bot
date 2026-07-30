"""Opt-in marketplace module — a storefront an org sells through.

fi-INDEPENDENT: plain FastAPI + pydantic + swappable stores + a payment seam.
Enable it by adding ``marketplace`` to ``APP_MODULES`` (see ``app.modules``).
Real payments (Stripe / MercadoPago) plug in by swapping the default
``FakePaymentGateway`` — the module code does not change.

``marketplace_router`` resolves lazily (PEP 562), same as the CMS module: importing
the pure-pydantic halves — ``app.marketplace.models``, ``app.marketplace.store`` —
then costs nothing but pydantic. Eagerly importing the router drags ``app.auth``
(and with it slowapi and the whole web stack) into every consumer of the models,
so a seed validator or a catalogue script dies with ModuleNotFoundError outside
the API environment, for code that never needed a web framework.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .routes import marketplace_router

__all__ = ["marketplace_router"]


def __getattr__(name: str):
    if name == "marketplace_router":
        from .routes import marketplace_router

        return marketplace_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
