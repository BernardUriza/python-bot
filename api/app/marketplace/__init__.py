"""Opt-in marketplace module — a storefront an org sells through.

fi-INDEPENDENT: plain FastAPI + pydantic + swappable stores + a payment seam.
Enable it by adding ``marketplace`` to ``APP_MODULES`` (see ``app.modules``).
Real payments (Stripe / MercadoPago) plug in by swapping the default
``FakePaymentGateway`` — the module code does not change.
"""
from __future__ import annotations

from .routes import marketplace_router

__all__ = ["marketplace_router"]
