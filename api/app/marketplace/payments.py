"""Payment seam. The module charges through a ``PaymentGateway`` it never
constructs directly — it asks ``payment_gateway()`` for the process default. A
consumer that wants real money swaps the singleton for a Stripe / MercadoPago
adapter (same two-method shape); no route or store code changes. This is the
opt-in 'level' the marketplace adds, kept fake-by-default so the tracer bullet
charges nothing.

Fail-closed level: set ``APP_MARKETPLACE_LIVE`` once a consumer accepts real
buyers. With it set, ``active_payment_gateway()`` refuses the fake gateway so
``/pay`` can never mark an order paid without money actually moving. Unset
(dev / test / default) keeps the fake gateway — existing behavior unchanged.
"""
from __future__ import annotations

import os
import uuid
from typing import Protocol, runtime_checkable

from .models import Order


class PaymentResult:
    def __init__(self, *, ok: bool, reference: str | None, error: str | None = None) -> None:
        self.ok = ok
        self.reference = reference
        self.error = error


@runtime_checkable
class PaymentGateway(Protocol):
    def charge(self, order: Order) -> PaymentResult: ...


class FakePaymentGateway:
    """Always-approves gateway for dev / tests. Returns a synthetic reference so
    the order can record 'how it was paid' without touching a real processor."""

    def charge(self, order: Order) -> PaymentResult:
        return PaymentResult(ok=True, reference=f"fake_{uuid.uuid4().hex[:16]}")


_GATEWAY: PaymentGateway = FakePaymentGateway()


def payment_gateway() -> PaymentGateway:
    return _GATEWAY


def set_payment_gateway(gateway: PaymentGateway) -> None:
    """Swap the process gateway (real adapter in prod, a stub in tests)."""
    global _GATEWAY
    _GATEWAY = gateway


class PaymentGatewayNotConfigured(Exception):
    """Marketplace is live but only the fake gateway is wired — fail-closed so a
    real buyer is never marked paid without money actually moving."""


def _marketplace_is_live() -> bool:
    return (os.getenv("APP_MARKETPLACE_LIVE") or "").strip().lower() in {"1", "true", "yes", "on"}


def active_payment_gateway() -> PaymentGateway:
    """The process gateway with a fail-closed guard: when ``APP_MARKETPLACE_LIVE``
    is set, refuse ``FakePaymentGateway`` so ``/pay`` cannot mark an order paid
    without a real charge. Flag unset keeps current dev / test behavior."""
    gateway = _GATEWAY
    if _marketplace_is_live() and isinstance(gateway, FakePaymentGateway):
        raise PaymentGatewayNotConfigured(
            "APP_MARKETPLACE_LIVE is set but no real payment gateway is configured; "
            "wire one via set_payment_gateway() before accepting payments"
        )
    return gateway
