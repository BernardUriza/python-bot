"""HTTP face for the marketplace module.

Public: browse the published catalog and place an order (a buyer needs no key).
Gated by ``verify_api_key``: create/patch/publish/delete a product, the admin
product listing, and the order ledger. Payment runs through the swappable
``payment_gateway()`` seam.
"""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_api_key
from .models import (
    Order,
    OrderLine,
    OrderRequest,
    Product,
    ProductDraft,
    ProductPatch,
)
from .payments import payment_gateway
from .store import SlugTaken, order_store, product_store

marketplace_router = APIRouter(prefix="/marketplace", tags=["marketplace"])

_gated = [Depends(verify_api_key)]


# ---- products ----

@marketplace_router.post("/products", status_code=201, dependencies=_gated)
async def create_product(draft: ProductDraft) -> Product:
    try:
        return product_store().create(draft)
    except SlugTaken:
        raise HTTPException(status_code=409, detail=f"slug already exists: {draft.slug}")


@marketplace_router.put("/products/{product_id}", dependencies=_gated)
async def update_product(product_id: str, patch: ProductPatch) -> Product:
    try:
        product = product_store().patch(product_id, patch)
    except SlugTaken as e:
        raise HTTPException(status_code=409, detail=f"slug already exists: {e}")
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@marketplace_router.post("/products/{product_id}/publish", dependencies=_gated)
async def publish_product(product_id: str) -> Product:
    product = product_store().publish(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@marketplace_router.delete("/products/{product_id}", status_code=204, dependencies=_gated)
async def delete_product(product_id: str) -> None:
    if not product_store().delete(product_id):
        raise HTTPException(status_code=404, detail="product not found")


@marketplace_router.get("/products")
async def list_published_products() -> list[Product]:
    return product_store().list(published_only=True)


@marketplace_router.get("/admin/products", dependencies=_gated)
async def list_all_products() -> list[Product]:
    return product_store().list(published_only=False)


@marketplace_router.get("/products/{slug}")
async def get_published_product(slug: str) -> Product:
    product = product_store().get_published_by_slug(slug)
    if product is None:
        raise HTTPException(status_code=404, detail="published product not found")
    return product


# ---- orders ----

@marketplace_router.post("/orders", status_code=201)
async def place_order(req: OrderRequest) -> Order:
    products = product_store()
    lines: list[OrderLine] = []
    currency: str | None = None
    for item in req.items:
        product = products.get(item.product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"product not found: {item.product_id}")
        if product.status != "published":
            raise HTTPException(status_code=409, detail=f"product not available: {item.product_id}")
        if product.stock < item.quantity:
            raise HTTPException(status_code=409, detail=f"insufficient stock: {item.product_id}")
        if currency is None:
            currency = product.currency
        elif currency != product.currency:
            raise HTTPException(status_code=400, detail="mixed currencies in one order")
        lines.append(OrderLine(
            product_id=product.id, slug=product.slug, title=product.title,
            unit_price_cents=product.price_cents, quantity=item.quantity,
        ))
    total = sum(line.unit_price_cents * line.quantity for line in lines)
    now = time.time()
    order = Order(
        id=uuid.uuid4().hex, lines=lines, total_cents=total, currency=currency or "MXN",
        buyer_name=req.buyer_name, buyer_contact=req.buyer_contact,
        status="pending", payment_reference=None, created_at=now, updated_at=now,
    )
    return order_store().save(order)


@marketplace_router.post("/orders/{order_id}/pay")
async def pay_order(order_id: str) -> Order:
    orders = order_store()
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.status != "pending":
        raise HTTPException(status_code=409, detail=f"order is {order.status}, not payable")

    products = product_store()
    for line in order.lines:
        product = products.get(line.product_id)
        if product is None or product.stock < line.quantity:
            raise HTTPException(status_code=409, detail=f"insufficient stock: {line.product_id}")

    result = payment_gateway().charge(order)
    if not result.ok:
        raise HTTPException(status_code=402, detail=result.error or "payment failed")

    for line in order.lines:
        products.decrement_stock(line.product_id, line.quantity)
    paid = order.model_copy(update={
        "status": "paid", "payment_reference": result.reference, "updated_at": max(time.time(), order.updated_at),
    })
    return orders.save(paid)


@marketplace_router.get("/orders", dependencies=_gated)
async def list_orders() -> list[Order]:
    return order_store().list()
