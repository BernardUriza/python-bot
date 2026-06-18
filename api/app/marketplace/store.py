"""Process-wide product + order stores. In-memory by default (a restart wipes
them) — swap for a Postgres-backed pair (same methods) for real persistence,
mirroring ``app.store``. No other code changes."""
from __future__ import annotations

import time
import uuid

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
        product = self._items[product_id]
        self._items[product_id] = product.model_copy(update={"stock": product.stock - qty, "updated_at": max(time.time(), product.updated_at)})


class InMemoryOrderStore:
    def __init__(self) -> None:
        self._items: dict[str, Order] = {}

    def clear(self) -> None:
        self._items.clear()

    def save(self, order: Order) -> Order:
        self._items[order.id] = order
        return order

    def get(self, order_id: str) -> Order | None:
        return self._items.get(order_id)

    def list(self) -> list[Order]:
        return sorted(self._items.values(), key=lambda o: o.created_at)


_PRODUCT_STORE = InMemoryProductStore()
_ORDER_STORE = InMemoryOrderStore()


def product_store() -> InMemoryProductStore:
    return _PRODUCT_STORE


def order_store() -> InMemoryOrderStore:
    return _ORDER_STORE
