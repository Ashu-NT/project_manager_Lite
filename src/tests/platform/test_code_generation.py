"""Tests for the shared entity code generator."""

from __future__ import annotations

import pytest

from src.core.platform.common.code_generation import (
    CodeGenerator,
    assert_code_unique,
    compose_code,
    generate_unique_code,
    is_valid_code,
    normalize_manual_code,
    sanitize_token,
)
from src.core.platform.common.exceptions import ValidationError


# ── sanitize_token ───────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "value,expected",
    [
        ("ACME Corp", "ACME"),
        ("Electrical Crew", "ELEC"),
        ("Pump, Assembly", "PUMP"),
        ("  spaced  ", "SPAC"),
        ("a-b_c", "A"),
        ("", ""),
        (None, ""),
        ("!!!", ""),
    ],
)
def test_sanitize_token(value, expected):
    assert sanitize_token(value) == expected


def test_sanitize_token_respects_max_length():
    assert sanitize_token("Refinery", max_length=6) == "REFINE"


# ── compose_code ─────────────────────────────────────────────────────────────
def test_compose_code_with_segment():
    assert compose_code("PRJ", sequence=1, segment="2026") == "PRJ-2026-0001"
    assert compose_code("CLI", sequence=1, segment="ACME") == "CLI-ACME-0001"


def test_compose_code_without_segment():
    assert compose_code("PO", sequence=42, segment="") == "PO-0042"


def test_compose_code_custom_width():
    assert compose_code("WO", sequence=7, segment="2026", width=6) == "WO-2026-000007"


# ── generate_unique_code ─────────────────────────────────────────────────────
def test_generate_unique_code_skips_taken_sequences():
    taken = {"RES-ELEC-0001", "RES-ELEC-0002"}
    code = generate_unique_code("RES", exists=lambda c: c in taken, segment="ELEC")
    assert code == "RES-ELEC-0003"


def test_generate_unique_code_first_free():
    code = generate_unique_code("PO", exists=lambda c: False, segment="2026")
    assert code == "PO-2026-0001"


def test_generate_unique_code_raises_when_exhausted():
    with pytest.raises(ValidationError) as exc:
        generate_unique_code("X", exists=lambda c: True, max_attempts=5)
    assert exc.value.code == "CODE_GENERATION_EXHAUSTED"


# ── normalize / validate manual codes ────────────────────────────────────────
@pytest.mark.parametrize(
    "value,expected",
    [
        ("prj 2026 0001", "PRJ-2026-0001"),
        ("  acme//corp  ", "ACME-CORP"),
        ("ABC-001", "ABC-001"),
        ("--weird__", "WEIRD"),
        (None, ""),
    ],
)
def test_normalize_manual_code(value, expected):
    assert normalize_manual_code(value) == expected


@pytest.mark.parametrize(
    "value,valid",
    [
        ("PRJ-2026-0001", True),
        ("ITM-PUMP-0007", True),
        ("ABC", True),
        ("", False),
        ("has space", False),
        ("-leading", False),
        ("trailing-", False),
        ("x" * 65, False),
    ],
)
def test_is_valid_code(value, valid):
    assert is_valid_code(value) is valid


def test_assert_code_unique_passes_when_free():
    assert_code_unique("PRJ-2026-0001", exists=lambda c: False)  # no raise


def test_assert_code_unique_raises_on_collision():
    with pytest.raises(ValidationError) as exc:
        assert_code_unique("PRJ-2026-0001", exists=lambda c: True, label="Project code")
    assert exc.value.code == "CODE_DUPLICATE"
    assert "Project code" in str(exc.value)


# ── CodeGenerator ────────────────────────────────────────────────────────────
def test_generator_uses_name_token():
    gen = CodeGenerator()
    assert gen.generate("client", name="ACME Corp", exists=lambda c: False) == "CLI-ACME-0001"


def test_generator_uses_year_when_no_name():
    gen = CodeGenerator()
    assert gen.generate("project", year=2026, exists=lambda c: False) == "PRJ-2026-0001"


def test_generator_context_overrides_name():
    gen = CodeGenerator()
    code = gen.generate("item", name="ignored", context="Pump", exists=lambda c: False)
    assert code == "ITM-PUMP-0001"


def test_generator_increments_for_existing_codes():
    gen = CodeGenerator()
    taken = {"ITM-PUMP-0001", "ITM-PUMP-0002", "ITM-PUMP-0003", "ITM-PUMP-0004", "ITM-PUMP-0005", "ITM-PUMP-0006"}
    code = gen.generate("item", context="Pump", exists=lambda c: c in taken)
    assert code == "ITM-PUMP-0007"


def test_generator_plain_prefix_sequence_without_segment():
    gen = CodeGenerator()
    assert gen.generate("task", exists=lambda c: False) == "TSK-0001"


def test_generator_custom_prefix_override():
    gen = CodeGenerator(prefixes={"gadget": "GDT"})
    assert gen.generate("gadget", year=2026, exists=lambda c: False) == "GDT-2026-0001"


def test_generator_unknown_entity_derives_prefix():
    gen = CodeGenerator()
    # not in the map -> derived from the entity type token
    assert gen.generate("Widget", exists=lambda c: False) == "WIDG-0001"


def test_generator_blank_entity_raises():
    gen = CodeGenerator()
    with pytest.raises(ValidationError) as exc:
        gen.generate("   ", exists=lambda c: False)
    assert exc.value.code == "CODE_ENTITY_UNKNOWN"
