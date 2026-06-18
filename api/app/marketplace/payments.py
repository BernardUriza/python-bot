"""Payment seam. The module charges through a ``PaymentGateway`` it never
constructs directly — it asks ``payment_gateway()`` for the process default. A
consumer that wants real money swaps the singleton for a Stripe / MercadoPago
adapter (same two-method shape); no route or store code changes. This is the
opt-in 'level' the marketplace adds, kept fake-by-default so the tracer bullet
charges nothing.
"""
from __future__ import annotations

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
