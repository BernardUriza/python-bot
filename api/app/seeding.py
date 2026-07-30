"""Boot-time seeding for the opt-in content stores (CMS, marketplace).

An org's canonical catalogue — its crónicas, its products — usually lives in its
repo (reviewed, versioned, approved out-of-band) long before anyone touches an
admin UI. Without this, that content only enters over HTTP, so every cold start
of a container with the default in-memory stores serves an empty surface until a
human re-runs a loader script. Point an env var at a JSON file and the store
re-applies it on every boot.

ONE seeder serves every module: ``InMemoryContentStore`` and
``InMemoryProductStore`` expose the same ``create(draft)`` / ``publish(id)``
contract, so the algorithm is identical and only the draft model, the store and
the env var change. A second copy per module would be duplication wearing a
different name.

File shape — ``{"items": [...]}``, where each item is either a flat draft or an
object carrying the draft under ``payload`` (so an org can keep its own editorial
metadata beside it in the same file, single source of truth). Two optional flags
live at the item root: ``publish: true`` publishes what this seeder creates, and
``skip: true`` keeps an item in the file without ever loading it (an org's record
of content it decided NOT to serve)::

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
- **Never fatal.** A missing file, malformed JSON, a rejected draft or a store
  that refuses a row all degrade to a warning and a report. This runs at import
  time: anything that raises here is a container that will not boot, i.e. the
  org's whole API down over one bad row. A thin surface beats a dead one.
- **Publishing is opt-in per item.** ``publish`` defaults to false, so the
  approval gate stays where the org put it.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

_log = logging.getLogger("app.seeding")

CMS_SEED_FILE_ENV = "CMS_SEED_FILE"
MARKETPLACE_SEED_FILE_ENV = "MARKETPLACE_SEED_FILE"

_ITEM_FLAGS = ("publish", "skip")


class SeedableStore(Protocol):
    def create(self, draft): ...
    def publish(self, item_id: str): ...


@dataclass
class SeedReport:
    created: list[str] = field(default_factory=list)
    published: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)
    error: str | None = None


def _entries(raw: object) -> list[dict]:
    items = raw.get("items") if isinstance(raw, dict) else raw
    return [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []


def _payload_of(entry: dict) -> dict:
    nested = entry.get("payload")
    if isinstance(nested, dict):
        return nested
    return {k: v for k, v in entry.items() if k not in _ITEM_FLAGS}


def _label(entry: dict) -> str:
    return str(_payload_of(entry).get("slug") or "<sin slug>")


def _is_slug_taken(exc: Exception) -> bool:
    # Each module raises its OWN SlugTaken, so matching by name keeps this seeder
    # from importing either one. Walking the MRO means a subclass still counts;
    # a rename shows up as "unexpected" and is reported, never fatal.
    return any(base.__name__ == "SlugTaken" for base in type(exc).__mro__)


def seed_store(store: SeedableStore, path: str | Path, draft_model) -> SeedReport:
    """Apply ``path`` to ``store``, building each item with ``draft_model``.

    Never raises on bad input — inspect the report.
    """
    report = SeedReport()
    path = Path(path)

    try:
        raw = json.loads(path.read_text(encoding="utf8"))
    except FileNotFoundError:
        report.error = f"seed file not found: {path}"
        _log.warning("%s — store starts empty", report.error)
        return report
    except (OSError, json.JSONDecodeError) as e:
        report.error = f"seed file unreadable ({path}): {e}"
        _log.warning("%s — store starts empty", report.error)
        return report

    for entry in _entries(raw):
        if entry.get("skip"):
            report.ignored.append(_label(entry))
            continue

        try:
            draft = draft_model(**_payload_of(entry))
        except Exception as e:
            report.invalid.append(_label(entry))
            _log.warning("seed item %s rejected: %s", _label(entry), e)
            continue

        try:
            item = store.create(draft)
        except Exception as e:
            if _is_slug_taken(e):
                report.skipped.append(draft.slug)
            else:
                # NEVER fatal. This runs at import time, so a raise here is a
                # container that will not boot — the org's whole API down over
                # one bad row. Report it and keep seeding the rest.
                report.invalid.append(draft.slug)
                _log.warning("seed item %s could not be created: %r", draft.slug, e)
            continue

        report.created.append(draft.slug)
        if entry.get("publish"):
            if store.publish(item.id) is None:
                # The store took it and then could not find it: the report must
                # not claim a publish that did not happen.
                report.invalid.append(draft.slug)
                _log.warning("seed item %s created but publish found nothing", draft.slug)
            else:
                report.published.append(draft.slug)

    _log.info(
        "seed from %s — created=%d published=%d already-there=%d ignored=%d invalid=%d",
        path, len(report.created), len(report.published),
        len(report.skipped), len(report.ignored), len(report.invalid),
    )
    return report


def seed_from_env(store: SeedableStore, draft_model, env_var: str) -> SeedReport | None:
    """Seed from the file named by ``env_var`` if it is set; otherwise a no-op."""
    configured = (os.getenv(env_var) or "").strip()
    if not configured:
        return None
    return seed_store(store, configured, draft_model)
