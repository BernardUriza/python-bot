"""Storefront shapes. Money is integer minor units (cents) — never floats — to
avoid rounding drift. ``extra = "forbid"`` so an unknown field fails loudly."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProductStatus = Literal["draft", "published"]
OrderStatus = Literal["pending", "paid", "cancelled"]

SLUG_MAX = 160
TITLE_MAX = 300
DESC_MAX = 20_000
PRICE_MAX = 100_000_000  # 1,000,000.00 in cents — a sane ceiling


class ProductDraft(BaseModel):
    slug: str = Field(..., min_length=1, max_length=SLUG_MAX)
    title: str = Field(..., min_length=1, max_length=TITLE_MAX)
    description: str = Field(..., min_length=1, max_length=DESC_MAX)
    price_cents: int = Field(..., ge=0, le=PRICE_MAX)
    currency: str = Field(default="MXN", min_length=3, max_length=3)
    stock: int = Field(..., ge=0)
    seller: str = Field(..., min_length=1, max_length=TITLE_MAX)
    image_url: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class ProductPatch(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=SLUG_MAX)
    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)
    description: str | None = Field(default=None, min_length=1, max_length=DESC_MAX)
    price_cents: int | None = Field(default=None, ge=0, le=PRICE_MAX)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    stock: int | None = Field(default=None, ge=0)
    seller: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)
    image_url: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class Product(BaseModel):
    id: str
    slug: str
    title: str
    description: str
    price_cents: int
    currency: str
    stock: int
    seller: str
    image_url: str | None
    status: ProductStatus
    created_at: float
    updated_at: float


class OrderLineInput(BaseModel):
    product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1, le=1000)

    model_config = ConfigDict(extra="forbid")


class OrderRequest(BaseModel):
    buyer_name: str = Field(..., min_length=1, max_length=TITLE_MAX)
    buyer_contact: str = Field(..., min_length=1, max_length=TITLE_MAX)
    items: list[OrderLineInput] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class OrderLine(BaseModel):
    product_id: str
    slug: str
    title: str
    unit_price_cents: int
    quantity: int


class Order(BaseModel):
    id: str
    lines: list[OrderLine]
    total_cents: int
    currency: str
    buyer_name: str
    buyer_contact: str
    status: OrderStatus
    payment_reference: str | None
    created_at: float
    updated_at: float
