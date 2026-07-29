"""Unit tests for the input-validation helpers — the API's first line of
defence against junk/oversized/abusive input before a turn ever starts."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.validation import (
    clean_optional_id,
    clean_text,
    public_error_message,
    validate_backend,
    validate_id,
)


def test_clean_text_strips_and_returns():
    assert clean_text("  hi  ", field="message", max_chars=10) == "hi"


def test_clean_text_rejects_empty():
    with pytest.raises(HTTPException) as exc:
        clean_text("   ", field="message", max_chars=10)
    assert exc.value.status_code == 400


def test_clean_text_rejects_too_long():
    with pytest.raises(HTTPException) as exc:
        clean_text("x" * 11, field="message", max_chars=10)
    assert exc.value.status_code == 413


@pytest.mark.parametrize("good", ["abc", "a.b:c-d_e", "A1", "x" * 128])
def test_validate_id_accepts_valid(good):
    assert validate_id(good, field="corpus_id") == good


@pytest.mark.parametrize("bad", ["", "_leading", "has space", "x" * 129, "bad/slash"])
def test_validate_id_rejects_invalid(bad):
    with pytest.raises(HTTPException) as exc:
        validate_id(bad, field="corpus_id")
    assert exc.value.status_code == 400


def test_clean_optional_id_passthrough_none_and_blank():
    assert clean_optional_id(None, field="corpus_id") is None
    assert clean_optional_id("   ", field="corpus_id") is None


def test_validate_backend_none_passes_through():
    assert validate_backend(None) is None


def test_validate_backend_normalizes_case():
    assert validate_backend("CLAUDE") == "claude"


def test_validate_backend_rejects_unknown():
    with pytest.raises(HTTPException) as exc:
        validate_backend("gpt5")
    assert exc.value.status_code == 400


def test_public_error_message_hides_internals():
    msg = public_error_message(ValueError("secret stack detail"))
    assert "secret" not in msg
    assert msg == "request failed while generating a response"


def test_public_error_message_timeout_is_specific():
    assert "timeout" in public_error_message(TimeoutError())
