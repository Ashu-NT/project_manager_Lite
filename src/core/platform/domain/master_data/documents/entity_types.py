from __future__ import annotations

from enum import Enum


class DocumentEntityType(str, Enum):
    """Canonical vocabulary of entity types explicitly approved to use the
    generic DocumentLink relationship end-to-end (desktop API / presenter /
    controller boundary). This is NOT a schema constraint -- DocumentLink's
    own `entity_type` column stays a free string at the domain/ORM layer
    (see document_link.py), so approving a new integration never requires a
    migration. Add a member only once a real, reviewed vertical slice for
    that entity has shipped -- the generic mechanism being technically
    capable of linking to any entity is never itself justification (Party,
    for example, is deliberately not a member here despite being technically
    possible, pending a separate, explicit product decision)."""

    EMPLOYEE = "employee"


__all__ = ["DocumentEntityType"]
