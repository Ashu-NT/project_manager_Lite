"""Shared, context-aware entity code generation for every module.

Produces meaningful, human-readable, unique codes — not random strings —
such as::

    PRJ-2026-0001    CLI-ACME-0001    RES-ELEC-0003    ITM-PUMP-0007    PO-2026-0042

Design notes
------------
* Backend-only and **repository-agnostic**: callers pass an ``exists(code)``
  callback, so uniqueness is enforced against whatever table/repository owns the
  code. The generator never talks to a database directly.
* QML-suggested or manually entered codes must still be validated on save —
  use :func:`normalize_manual_code` + :func:`assert_code_unique`. The backend
  never trusts a code that arrived from the UI.
* Deterministic: the same inputs + same ``exists`` state yield the same code.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date

from src.core.platform.common.exceptions import ValidationError

# Canonical entity -> prefix map. Callers may extend/override via CodeGenerator.
ENTITY_PREFIXES: dict[str, str] = {
    "project": "PRJ",
    "task": "TSK",
    "resource": "RES",
    "client": "CLI",
    "vendor": "VEN",
    "item": "ITM",
    "purchase_order": "PO",
    "work_order": "WO",
    "asset": "AST",
    "document": "DOC",
    "risk": "RSK",
    "cost": "CST",
    # entities that already carry user-facing codes today
    "organization": "ORG",
    "site": "SITE",
    "department": "DEPT",
    "employee": "EMP",
    "party": "PTY",
    "document_structure": "DST",
    "category": "CAT",
    "storeroom": "STR",
    "location": "LOC",
    "component": "CMP",
    "system": "SYS",
    "requisition": "REQ",
    "receipt": "RCV",
}

MAX_CODE_LENGTH = 64
DEFAULT_SEQUENCE_WIDTH = 4
DEFAULT_TOKEN_LENGTH = 4

_NON_ALNUM = re.compile(r"[^A-Z0-9]+")
_VALID_CODE = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$")


def sanitize_token(value: str | None, *, max_length: int = DEFAULT_TOKEN_LENGTH) -> str:
    """Turn a display name into a compact, safe code token.

    Uppercases, drops unsafe characters, and keeps the leading word truncated to
    ``max_length``::

        "ACME Corp"        -> "ACME"
        "Electrical Crew"  -> "ELEC"
        "Pump, Assembly"   -> "PUMP"
        ""                 -> ""
    """
    if not value:
        return ""
    words = [word for word in _NON_ALNUM.split(value.strip().upper()) if word]
    if not words:
        return ""
    return words[0][:max_length]


def compose_code(
    prefix: str,
    *,
    sequence: int,
    segment: str = "",
    width: int = DEFAULT_SEQUENCE_WIDTH,
) -> str:
    """Assemble ``PREFIX[-SEGMENT]-NNNN`` from its parts."""
    parts = [prefix]
    if segment:
        parts.append(segment)
    parts.append(str(int(sequence)).zfill(width))
    return "-".join(parts)


def generate_unique_code(
    prefix: str,
    *,
    exists: Callable[[str], bool],
    segment: str = "",
    width: int = DEFAULT_SEQUENCE_WIDTH,
    start: int = 1,
    max_attempts: int = 100_000,
) -> str:
    """Return the lowest free ``PREFIX[-SEGMENT]-NNNN`` not rejected by ``exists``."""
    sequence = max(int(start), 1)
    for _ in range(max_attempts):
        candidate = compose_code(prefix, sequence=sequence, segment=segment, width=width)
        if not exists(candidate):
            return candidate
        sequence += 1
    raise ValidationError(
        "Unable to generate a unique code after too many attempts.",
        code="CODE_GENERATION_EXHAUSTED",
    )


def normalize_manual_code(value: str | None, *, max_length: int = MAX_CODE_LENGTH) -> str:
    """Normalize a manually entered code: uppercase, unsafe runs -> ``-``, trimmed."""
    if value is None:
        return ""
    cleaned = _NON_ALNUM.sub("-", value.strip().upper()).strip("-")
    return cleaned[:max_length]


def is_valid_code(value: str | None) -> bool:
    """True if ``value`` is a non-empty, normalized code within the length limit."""
    if not value:
        return False
    return len(value) <= MAX_CODE_LENGTH and bool(_VALID_CODE.match(value))


def assert_code_unique(
    code: str,
    *,
    exists: Callable[[str], bool],
    label: str = "Code",
) -> None:
    """Raise :class:`ValidationError` if ``exists(code)`` reports a collision."""
    if exists(code):
        raise ValidationError(f"{label} '{code}' already exists.", code="CODE_DUPLICATE")


class CodeGenerator:
    """Context-aware code generator, reusable by every module.

    Example::

        gen = CodeGenerator()
        gen.generate("client", name="ACME Corp", exists=repo_has_code)   # CLI-ACME-0001
        gen.generate("project", use_year=True, exists=repo_has_code)     # PRJ-2026-0001
    """

    def __init__(self, prefixes: dict[str, str] | None = None) -> None:
        self._prefixes = dict(ENTITY_PREFIXES)
        if prefixes:
            self._prefixes.update({str(k).lower(): str(v).upper() for k, v in prefixes.items()})

    def resolve_prefix(self, entity_type: str) -> str:
        key = (entity_type or "").strip().lower()
        prefix = self._prefixes.get(key)
        if prefix:
            return prefix
        derived = sanitize_token(entity_type, max_length=4)
        if not derived:
            raise ValidationError(
                "An entity type is required to generate a code.",
                code="CODE_ENTITY_UNKNOWN",
            )
        return derived

    def generate(
        self,
        entity_type: str,
        *,
        exists: Callable[[str], bool],
        name: str | None = None,
        context: str | None = None,
        year: int | None = None,
        use_year: bool = False,
        width: int = DEFAULT_SEQUENCE_WIDTH,
        token_length: int = DEFAULT_TOKEN_LENGTH,
        start: int = 1,
    ) -> str:
        """Generate a unique code for ``entity_type``.

        Segment selection (the middle part): explicit ``context`` token wins,
        then a token derived from ``name``; otherwise the year is used when
        ``use_year`` is set or a ``year`` is given. With none of those, the code
        is just ``PREFIX-NNNN``.
        """
        prefix = self.resolve_prefix(entity_type)
        segment = ""
        if context:
            segment = sanitize_token(context, max_length=token_length)
        elif name:
            segment = sanitize_token(name, max_length=token_length)
        if not segment and (use_year or year is not None):
            segment = str(year if year is not None else date.today().year)
        return generate_unique_code(
            prefix, exists=exists, segment=segment, width=width, start=start
        )


__all__ = [
    "CodeGenerator",
    "ENTITY_PREFIXES",
    "MAX_CODE_LENGTH",
    "assert_code_unique",
    "compose_code",
    "generate_unique_code",
    "is_valid_code",
    "normalize_manual_code",
    "sanitize_token",
]
