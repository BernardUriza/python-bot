"""TDD for the opt-in marketplace module — a storefront an org sells through
(e.g. a tianguis: ropa, arte, libros, fanzines). fi-INDEPENDENT: mounts on a
bare FastAPI app, no fi_runner.  python -m pytest tests/test_marketplace.py
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.marketplace import marketplace_router
from app.marketplace.payments import (
    FakePaymentGateway,
    PaymentResult,
    set_payment_gateway,
)
from app.marketplace.store import order_store, product_store


@pytest.fixture()
def client() -> TestClient:
    product_store().clear()
    order_store().clear()
    app = FastAPI()
    app.include_router(marketplace_router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_payment_gateway():
    yield
    set_payment_gateway(FakePaymentGateway())


class _DecliningGateway:
    def charge(self, order) -> PaymentResult:
        return PaymentResult(ok=False, reference=None, error="declined")


def _product(client: TestClient, *, publish: bool = True, **over) -> dict:
    body = {"slug": "fanzine-mariposa", "title": "Fanzine Mariposa",
            "description": "Hecho a mano.", "price_cents": 15000, "currency": "MXN",
            "stock": 3, "seller": "Vendedora demo", **over}
    r = client.post("/marketplace/products", json=body)
    assert r.status_code == 201, r.text
    item = r.json()
    if publish:
        assert client.post(f"/marketplace/products/{item['id']}/publish").status_code == 200
        item["status"] = "published"
    return item


# ---- products ----

def test_product_starts_draft_and_hidden(client):
    p = _product(client, publish=False)
    assert p["status"] == "draft"
    assert client.get("/marketplace/products").json() == []


def test_publish_exposes_product_publicly(client):
    _product(client)
    listing = client.get("/marketplace/products").json()
    assert [p["slug"] for p in listing] == ["fanzine-mariposa"]
    assert client.get("/marketplace/products/fanzine-mariposa").json()["price_cents"] == 15000


def test_admin_listing_includes_drafts(client):
    _product(client, publish=False)
    assert client.get("/marketplace/admin/products").json()[0]["status"] == "draft"


def test_duplicate_product_slug_rejected(client):
    _product(client, publish=False)
    r = client.post("/marketplace/products", json={"slug": "fanzine-mariposa",
        "title": "x", "description": "y", "price_cents": 100, "currency": "MXN",
        "stock": 1, "seller": "a"})
    assert r.status_code == 409


# ---- orders ----

def test_order_computes_total_and_starts_pending(client):
    p = _product(client, stock=5)
    r = client.post("/marketplace/orders", json={
        "buyer_name": "Cliente", "buyer_contact": "cliente@example.com",
        "items": [{"product_id": p["id"], "quantity": 2}]})
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["status"] == "pending"
    assert order["total_cents"] == 30000
    assert order["currency"] == "MXN"


def test_order_for_unpublished_product_rejected(client):
    p = _product(client, publish=False)
    r = client.post("/marketplace/orders", json={"buyer_name": "C", "buyer_contact": "x",
        "items": [{"product_id": p["id"], "quantity": 1}]})
    assert r.status_code == 409


def test_order_exceeding_stock_rejected(client):
    p = _product(client, stock=1)
    r = client.post("/marketplace/orders", json={"buyer_name": "C", "buyer_contact": "x",
        "items": [{"product_id": p["id"], "quantity": 2}]})
    assert r.status_code == 409


def test_order_unknown_product_404(client):
    r = client.post("/marketplace/orders", json={"buyer_name": "C", "buyer_contact": "x",
        "items": [{"product_id": "nope", "quantity": 1}]})
    assert r.status_code == 404


def test_pay_marks_paid_and_decrements_stock(client):
    p = _product(client, stock=3)
    order = client.post("/marketplace/orders", json={"buyer_name": "C", "buyer_contact": "x",
        "items": [{"product_id": p["id"], "quantity": 2}]}).json()
    pay = client.post(f"/marketplace/orders/{order['id']}/pay")
    assert pay.status_code == 200
    body = pay.json()
    assert body["status"] == "paid"
    assert body["payment_reference"]  # the fake gateway returned a reference
    assert client.get("/marketplace/products/fanzine-mariposa").json()["stock"] == 1


def test_pay_twice_is_conflict(client):
    p = _product(client, stock=3)
    order = client.post("/marketplace/orders", json={"buyer_name": "C", "buyer_contact": "x",
        "items": [{"product_id": p["id"], "quantity": 1}]}).json()
    assert client.post(f"/marketplace/orders/{order['id']}/pay").status_code == 200
    assert client.post(f"/marketplace/orders/{order['id']}/pay").status_code == 409


def test_pay_unknown_order_404(client):
    assert client.post("/marketplace/orders/nope/pay").status_code == 404


def test_failed_payment_keeps_order_pending_and_stock_intact(client):
    set_payment_gateway(_DecliningGateway())
    p = _product(client, stock=3)
    order = client.post("/marketplace/orders", json={"buyer_name": "C", "buyer_contact": "x",
        "items": [{"product_id": p["id"], "quantity": 2}]}).json()
    pay = client.post(f"/marketplace/orders/{order['id']}/pay")
    assert pay.status_code == 402, pay.text
    assert client.get("/marketplace/products/fanzine-mariposa").json()["stock"] == 3


def test_live_marketplace_refuses_fake_gateway(client, monkeypatch):
    monkeypatch.setenv("APP_MARKETPLACE_LIVE", "1")
    p = _product(client, stock=3)
    order = client.post("/marketplace/orders", json={"buyer_name": "C", "buyer_contact": "x",
        "items": [{"product_id": p["id"], "quantity": 1}]}).json()
    pay = client.post(f"/marketplace/orders/{order['id']}/pay")
    assert pay.status_code == 503, pay.text
    assert client.get("/marketplace/products/fanzine-mariposa").json()["stock"] == 3
