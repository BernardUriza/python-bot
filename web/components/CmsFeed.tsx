"use client";

import { useEffect, useState } from "react";

import { API_KEY, apiUrl } from "../lib/api";

interface ContentItem {
  id: string;
  slug: string;
  title: string;
  body: string;
  author: string;
  created_at: number;
}

export function CmsFeed() {
  const [items, setItems] = useState<ContentItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(apiUrl("/cms/content"), {
      headers: API_KEY ? { "X-API-Key": API_KEY } : {},
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setItems)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="text-app-muted">No se pudo cargar el contenido: {error}</p>;
  if (!items) return <p className="text-app-muted">Cargando…</p>;
  if (items.length === 0) return <p className="text-app-muted">Aún no hay publicaciones.</p>;

  return (
    <ul className="space-y-4">
      {items.map((it) => (
        <li key={it.id} className="rounded-lg border border-app-border bg-app-surface p-4">
          <h3 className="text-lg font-semibold">{it.title}</h3>
          <p className="text-sm text-app-muted">por {it.author}</p>
          <p className="mt-2 whitespace-pre-line">{it.body}</p>
        </li>
      ))}
    </ul>
  );
}
