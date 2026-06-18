"use client";

import { useEffect, useState } from "react";

import { API_KEY, apiUrl } from "../lib/api";

interface Product {
  id: string;
  slug: string;
  title: string;
  description: string;
  price_cents: number;
  currency: string;
  stock: number;
  seller: string;
  image_url: string | null;
}

function formatPrice(cents: number, currency: string): string {
  try {
    return new Intl.NumberFormat("es-MX", { style: "currency", currency }).format(cents / 100);
  } catch {
    return `${(cents / 100).toFixed(2)} ${currency}`;
  }
}

export function MarketplaceCatalog() {
  const [items, setItems] = useState<Product[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(apiUrl("/marketplace/products"), {
      headers: API_KEY ? { "X-API-Key": API_KEY } : {},
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setItems)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="text-app-muted">No se pudo cargar la tienda: {error}</p>;
  if (!items) return <p className="text-app-muted">Cargando…</p>;
  if (items.length === 0) return <p className="text-app-muted">Aún no hay productos.</p>;

  return (
    <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {items.map((p) => (
        <li key={p.id} className="flex flex-col rounded-lg border border-app-border bg-app-surface p-4">
          {p.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={p.image_url} alt={p.title} className="mb-3 aspect-square w-full rounded object-cover" />
          ) : null}
          <h3 className="text-lg font-semibold">{p.title}</h3>
          <p className="text-sm text-app-muted">{p.seller}</p>
          <p className="mt-1 line-clamp-3 text-sm">{p.description}</p>
          <div className="mt-auto flex items-center justify-between pt-3">
            <span className="font-semibold text-app-accent">{formatPrice(p.price_cents, p.currency)}</span>
            <span className="text-xs text-app-muted">{p.stock > 0 ? `${p.stock} disp.` : "agotado"}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
