"""Optional-module selector — the thin view of the feature system that app.py
uses to decide which optional routers to mount.

The real logic (registry, dependency resolution, validation) lives in
``app.features``. This returns just the NON-core features so the mount loop in
``app.app`` doesn't try to "mount" the always-on chat.
"""
from __future__ import annotations

from .features import CORE_FEATURES, enabled_features


def enabled_optional_modules() -> set[str]:
    return enabled_features() - set(CORE_FEATURES)
