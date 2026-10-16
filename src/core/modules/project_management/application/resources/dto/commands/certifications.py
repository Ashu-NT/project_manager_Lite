from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ResourceAddCertificationCommand:
    resource_id: str
    certification_code: str
    certification_name: str
    issued_date: date | str | None = None
    expiry_date: date | str | None = None
    certificate_number: str = ""
    issuer: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ResourceUpdateCertificationCommand:
    cert_id: str
    expected_version: int
    certification_code: str
    certification_name: str
    issued_date: date | str | None = None
    expiry_date: date | str | None = None
    certificate_number: str = ""
    issuer: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ResourceRemoveCertificationCommand:
    cert_id: str
    expected_version: int
