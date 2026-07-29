"""Boot-time seeding for the CMS module.

An org's canonical content usually lives in its repo (reviewed, versioned,
approved out-of-band) long before anyone touches the admin UI. Without this, that
content only enters the store over HTTP — so every cold start of a container with
``InMemoryContentStore`` serves an empty feed until a human re-runs a loader
script. Point ``CMS_SEED_FILE`` at a JSON file and the store re-applies it on
every boot.

File shape — ``{"items": [...]}``, where each item is either a flat
``ContentDraft`` or an object carrying the draft under ``payload`` (so an org can
keep its own editorial metadata beside it in the same file, single source of
truth). Two optional flags live at the item root: ``publish: true`` publishes what this
seeder creates, and ``skip: true`` keeps an item in the file without ever loading
it (an org's record of content it decided NOT to serve)::

    {"items": [
      {"slug": "una", "title": "Una", "body": "…", "author": "Colectiva"},
      {"editorial": {"aprobado_por": "…"}, "publish": true,
       "payload": {"slug": "dos", "title": "Dos", "body": "…", "author": "Colectiva"}},
      {"slug": "vetada", "title": "Vetada", "body": "…", "author": "Colectiva",
       "skip": true}
    ]}

Three guarantees, in order of how much damage their absence would do:

- **Idempotent by slug.** A slug already in the store is the org's LIVE state;
  the seeder skips it entirely and never publishes it. A restart therefore cannot
  resurrect something a human took down.
- **Never fatal.** A missing file, malformed JSON, or a single bad item degrades
  to a warning and a report — a dead container is worse than a thin feed.
- **Publishing is opt-in per item.** ``publish`` defaults to false, so the
  approval gate stays where the org put it.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from .models import ContentDraft
from .store import SlugTaken

_log = logging.getLogger("app.cms.seed")

SEED_FILE_ENV = "CMS_SEED_FILE"


@dataclass
class SeedReport:
    created: list[str] = field(default_factory=list)
    published: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)
    error: str | None = None


def _entries(raw: object) -> list[dict]:
    if isinstance(raw, dict):
        items = raw.get("items")
    else:
        items = raw
    return [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []


_ITEM_FLAGS = ("publish", "skip")


def _payload_of(entry: dict) -> dict:
    nested = entry.get("payload")
    if isinstance(nested, dict):
        return nested
    return {k: v for k, v in entry.items() if k not in _ITEM_FLAGS}


def _draft_of(entry: dict) -> tuple[ContentDraft, bool]:
    return ContentDraft(**_payload_of(entry)), bool(entry.get("publish"))


def _label(entry: dict) -> str:
    return str(_payload_of(entry).get("slug") or "<sin slug>")


def seed_content_store(store, path: str | Path) -> SeedReport:
    """Apply ``path`` to ``store``. Never raises — inspect the report."""
    report = SeedReport()
    path = Path(path)

    try:
        raw = json.loads(path.read_text(encoding="utf8"))
    except FileNotFoundError:
        report.error = f"seed file not found: {path}"
        _log.warning("%s — CMS starts empty", report.error)
        return report
    except (OSError, json.JSONDecodeError) as e:
        report.error = f"seed file unreadable ({path}): {e}"
        _log.warning("%s — CMS starts empty", report.error)
        return report

    for entry in _entries(raw):
        if entry.get("skip"):
            report.ignored.append(_label(entry))
            continue
        try:
            draft, publish = _draft_of(entry)
        except Exception as e:
            report.invalid.append(_label(entry))
            _log.warning("seed item %s rejected: %s", _label(entry), e)
            continue

        try:
            item = store.create(draft)
        except SlugTaken:
            report.skipped.append(draft.slug)
            continue

        report.created.append(draft.slug)
        if publish:
            store.publish(item.id)
            report.published.append(draft.slug)

    _log.info(
        "CMS seed from %s — created=%d published=%d already-there=%d ignored=%d invalid=%d",
        path, len(report.created), len(report.published),
        len(report.skipped), len(report.ignored), len(report.invalid),
    )
    return report


def seed_from_env(store) -> SeedReport | None:
    """Seed from ``CMS_SEED_FILE`` if it is set; otherwise a no-op."""
    configured = (os.getenv(SEED_FILE_ENV) or "").strip()
    if not configured:
        return None
    return seed_content_store(store, configured)
