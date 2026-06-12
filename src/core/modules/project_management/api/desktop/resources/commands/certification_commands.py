from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceAddCertificationCommand:
    resource_id: str
    certification_code: str
    certification_name: str
    issued_date: str | None = None
    expiry_date: str | None = None
    issuing_body: str = ""
    notes: str = ""


__all__ = ["ResourceAddCertificationCommand"]
