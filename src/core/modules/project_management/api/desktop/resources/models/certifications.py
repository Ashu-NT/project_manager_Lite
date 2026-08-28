from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceCertificationDesktopDto:
    id: str
    resource_id: str
    certification_code: str
    certification_name: str
    issued_date: str | None
    expiry_date: str | None
    certificate_number: str
    issuer: str
    notes: str
    cert_status: str
    cert_status_label: str
    version: int


@dataclass(frozen=True)
class ResourceCertificationsPageDesktopDto:
    items: tuple[ResourceCertificationDesktopDto, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "certificationName"
    sort_direction: str = "asc"


__all__ = [
    "ResourceCertificationDesktopDto",
    "ResourceCertificationsPageDesktopDto",
]
