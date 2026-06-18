"""Feature-flag system — the single source of truth for what a given app is.

The template ships every capability, but no app uses all of them. Instead of
deleting code per consumer, an app DECLARES the subset it wants in the
``APP_MODULES`` env var; this module resolves that declaration into the concrete
set of enabled features, and the rest of the backend (and, mirrored, the web
front) reads from here.

What makes it 'intelligent' rather than a raw env list:
  - **core features** (the chat assistant) are always on — you can't ship the
    template with nothing;
  - declaring a feature **auto-enables its `requires`** (transitively), so a
    consumer never has to know a feature's internal dependencies;
  - **unknown keys are dropped with a warning**, never crashing the boot — a typo
    in APP_MODULES degrades to "that feature off", not a dead container.

The web mirror is ``web/lib/features.ts`` (build-time, so disabled features
tree-shake out of the bundle). Keep the two registries in sync — same keys,
same `requires`.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

_log = logging.getLogger("app.features")


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    core: bool = False
    requires: tuple[str, ...] = field(default=())


FEATURES: dict[str, Feature] = {
    "chat": Feature(key="chat", label="Asistente / chat", core=True),
    "cms": Feature(key="cms", label="Manejador de contenido"),
    "marketplace": Feature(key="marketplace", label="Marketplace / tienda"),
}

CORE_FEATURES: frozenset[str] = frozenset(k for k, f in FEATURES.items() if f.core)


def _parse(raw: str | None) -> list[str]:
    return [t.strip().lower() for t in (raw or "").split(",") if t.strip()]


def resolve_features(raw: str | None) -> set[str]:
    """Resolve an APP_MODULES declaration into the enabled feature set.

    Core features are always included; declared features pull in their
    ``requires`` transitively; unknown keys are dropped with a warning."""
    enabled: set[str] = set(CORE_FEATURES)
    pending = list(_parse(raw))
    seen: set[str] = set()
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        feature = FEATURES.get(key)
        if feature is None:
            _log.warning("APP_MODULES names unknown feature %r — ignored", key)
            continue
        enabled.add(key)
        pending.extend(feature.requires)
    return enabled


def enabled_features(raw: str | None = None) -> set[str]:
    """Enabled features for this process (reads APP_MODULES when raw is None)."""
    return resolve_features(os.getenv("APP_MODULES") if raw is None else raw)


# ---- HTTP face (fi-independent, always mounted) ----

from fastapi import APIRouter  # noqa: E402

feature_router = APIRouter(tags=["features"])


@feature_router.get("/features")
async def get_features() -> dict:
    """Advertise this app's composition — which capabilities are live. Honest
    observability: a consumer/operator reads the real running shape, not a guess."""
    enabled = enabled_features()
    return {
        "enabled": sorted(enabled),
        "features": {
            key: {
                "label": f.label,
                "core": f.core,
                "requires": list(f.requires),
                "enabled": key in enabled,
            }
            for key, f in FEATURES.items()
        },
    }
