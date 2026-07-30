"""Process-wide product + order stores. In-memory by default (a restart wipes
them) — swap for a Postgres-backed pair (same methods) for real persistence,
mirroring ``app.store``. No other code changes."""
from __future__ import annotations

import time
import uuid
from typing import Callable

from .models import Order, Product, ProductDraft, ProductPatch


class SlugTaken(Exception):
    """A create/patch would collide with an existing product slug."""


class InMemoryProductStore:
    def __init__(self) -> None:
        self._items: dict[str, Product] = {}

    def clear(self) -> None:
        self._items.clear()

    def _slug_owner(self, slug: str) -> str | None:
        for p in self._items.values():
            if p.slug == slug:
                return p.id
        return None

    def create(self, draft: ProductDraft) -> Product:
        if self._slug_owner(draft.slug) is not None:
            raise SlugTaken(draft.slug)
        now = time.time()
        product = Product(
            id=uuid.uuid4().hex,
            status="draft",
            created_at=now,
            updated_at=now,
            **draft.model_dump(),
        )
        self._items[product.id] = product
        return product

    def get(self, product_id: str) -> Product | None:
        return self._items.get(product_id)

    def get_published_by_slug(self, slug: str) -> Product | None:
        for p in self._items.values():
            if p.slug == slug and p.status == "published":
                return p
        return None

    def list(self, *, published_only: bool) -> list[Product]:
        items = list(self._items.values())
        if published_only:
            items = [p for p in items if p.status == "published"]
        return sorted(items, key=lambda p: p.created_at)

    def patch(self, product_id: str, patch: ProductPatch) -> Product | None:
        product = self._items.get(product_id)
        if product is None:
            return None
        fields = patch.model_dump(exclude_unset=True)
        new_slug = fields.get("slug")
        if new_slug is not None:
            owner = self._slug_owner(new_slug)
            if owner is not None and owner != product_id:
                raise SlugTaken(new_slug)
        updated = product.model_copy(update={**fields, "updated_at": max(time.time(), product.updated_at)})
        self._items[product_id] = updated
        return updated

    def publish(self, product_id: str) -> Product | None:
        product = self._items.get(product_id)
        if product is None:
            return None
        updated = product.model_copy(update={"status": "published", "updated_at": max(time.time(), product.updated_at)})
        self._items[product_id] = updated
        return updated

    def delete(self, product_id: str) -> bool:
        return self._items.pop(product_id, None) is not None

    def decrement_stock(self, product_id: str, qty: int) -> None:
        self._shift_stock(product_id, -qty)

    def restore_stock(self, product_id: str, qty: int) -> None:
        """Give reserved units back — a payment that failed, an order evicted."""
        self._shift_stock(product_id, qty)

    def _shift_stock(self, product_id: str, delta: int) -> None:
        product = self._items.get(product_id)
        if product is None:  # product deleted while an order held its units
            return
        self._items[product_id] = product.model_copy(update={
            "stock": max(0, product.stock + delta),
            "updated_at": max(time.time(), product.updated_at),
        })


class InMemoryOrderStore:
    """Bounded on purpose. ``POST /orders`` is public and keyless — a buyer has
    no credentials — so an unbounded dict is a memory faucet anyone can open,
    and this process also serves the org's public content. Past ``max_orders``
    the oldest are evicted; ``on_evict`` lets the caller give their reserved
    stock back so an eviction can't quietly consume inventory."""

    def __init__(self, max_orders: int = 500) -> None:
        self._items: dict[str, Order] = {}
        self._max_orders = max_orders
        self.on_evict: Callable[[Order], None] | None = None

    def clear(self) -> None:
        self._items.clear()

    def save(self, order: Order) -> Order:
        self._items[order.id] = order
        self._evict_overflow()
        return order

    def _evict_overflow(self) -> None:
        while len(self._items) > self._max_orders:
            oldest = min(self._items.values(), key=lambda o: o.created_at)
            del self._items[oldest.id]
            if self.on_evict is not None:
                self.on_evict(oldest)

    def get(self, order_id: str) -> Order | None:
        return self._items.get(order_id)

    def list(self) -> list[Order]:
        return sorted(self._items.values(), key=lambda o: o.created_at)

    def expire_stale_pending(self, ttl_seconds: float, release) -> list[str]:
        """Cancel pending orders older than ``ttl_seconds`` and release their
        reserved units.

        A reservation with no expiry is how a real shop ends up showing
        everything as sold out: one buyer who never pays holds a one-of-a-kind
        piece forever. Lazy on purpose — no background task to keep alive, and a
        container that sleeps has nothing to sweep anyway.
        """
        cutoff = time.time() - ttl_seconds
        expired = [o for o in self._items.values()
                   if o.status == "pending" and o.created_at < cutoff]
        for order in expired:
            for line in order.lines:
                release(line.product_id, line.quantity)
            self._items[order.id] = order.model_copy(update={
                "status": "cancelled", "updated_at": max(time.time(), order.updated_at),
            })
        return [o.id for o in expired]


_PRODUCT_STORE = InMemoryProductStore()
_ORDER_STORE = InMemoryOrderStore()


def _release_reserved(order: Order) -> None:
    """An evicted order that never got paid was still holding units."""
    if order.status != "pending":
        return
    for line in order.lines:
        _PRODUCT_STORE.restore_stock(line.product_id, line.quantity)


_ORDER_STORE.on_evict = _release_reserved


def product_store() -> InMemoryProductStore:
    return _PRODUCT_STORE


def order_store() -> InMemoryOrderStore:
    return _ORDER_STORE
