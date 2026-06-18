"""Opt-in module selector — the seam that keeps the template lean.

The chat router is ALWAYS on. Optional capabilities (``cms``, ``marketplace``,
…) are mounted only when named in the ``APP_MODULES`` env var (comma-separated,
case-insensitive). A consumer that wants a content-managed site with a store
sets ``APP_MODULES=cms,marketplace``; a plain assistant leaves it unset and pays
nothing for what it doesn't use.
"""
from __future__ import annotations

import os


def enabled_optional_modules() -> set[str]:
    raw = (os.getenv("APP_MODULES") or "").strip()
    return {m.strip().lower() for m in raw.split(",") if m.strip()}
