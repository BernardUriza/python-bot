"""Payment seam. The module charges through a ``PaymentGateway`` it never
constructs directly — it asks ``payment_gateway()`` for the process default. A
consumer that wants real money swaps the singleton for a Stripe / MercadoPago
adapter (same two-method shape); no route or store code changes. This is the
opt-in 'level' the marketplace adds, kept fake-by-default so the tracer bullet
charges nothing.

Fail-closed in BOTH directions — the default is a gateway that refuses:

- **Nothing wired** (the default, and every deploy that hasn't opted in):
  ``/pay`` answers 503. Orders can still be placed; what is closed is the money.
- **``APP_MARKETPLACE_LIVE`` set but only the fake gateway wired**: 503 too, so a
  half-finished go-live can't mark real buyers paid.
- **A real adapter wired**: charges.

The fake gateway is opt-in for dev and tests (``set_payment_gateway``), never the
process default. It used to be, and that made "marketplace off" mean *payments
simulated as successful*: a buyer could place an order and get ``status: paid``
with a ``fake_…`` reference while no money moved. On a deployed API that is a
phantom-charge machine — the exact thing this seam exists to prevent, and the
thing an org selling on behalf of precarious people can least afford.
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


class ClosedPaymentGateway:
    """The default: no payment path is wired, so nothing can be charged. Never
    reached — ``active_payment_gateway()`` refuses it before ``charge`` runs."""

    def charge(self, order: Order) -> PaymentResult:  # pragma: no cover - guarded above
        return PaymentResult(ok=False, reference=None, error="no payment gateway configured")


_GATEWAY: PaymentGateway = ClosedPaymentGateway()


def payment_gateway() -> PaymentGateway:
    return _GATEWAY


def set_payment_gateway(gateway: PaymentGateway) -> None:
    """Swap the process gateway (real adapter in prod, a stub in tests)."""
    global _GATEWAY
    _GATEWAY = gateway


class PaymentGatewayNotConfigured(Exception):
    """No usable payment path — fail-closed so a buyer is never marked paid
    without money actually moving."""


def _marketplace_is_live() -> bool:
    return (os.getenv("APP_MARKETPLACE_LIVE") or "").strip().lower() in {"1", "true", "yes", "on"}


def active_payment_gateway() -> PaymentGateway:
    """The process gateway, or a refusal. Two ways to be closed, one to be open."""
    gateway = _GATEWAY
    if isinstance(gateway, ClosedPaymentGateway):
        raise PaymentGatewayNotConfigured(
            "no payment gateway is configured; this marketplace does not accept "
            "payments yet. Orders can be placed, but nothing can be charged"
        )
    if _marketplace_is_live() and isinstance(gateway, FakePaymentGateway):
        raise PaymentGatewayNotConfigured(
            "APP_MARKETPLACE_LIVE is set but only the fake gateway is wired; "
            "swap in a real adapter via set_payment_gateway() before accepting payments"
        )
    return gateway
