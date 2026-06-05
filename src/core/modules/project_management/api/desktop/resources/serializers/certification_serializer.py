from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.resources.models.certifications import (
    ResourceCertificationDesktopDto,
)


def serialize_certification(certification) -> ResourceCertificationDesktopDto:
    today = date.today()
    expiry = getattr(certification, "expiry_date", None)
    issued = getattr(certification, "issued_date", None)
    if expiry is None:
        status = "valid"
    elif expiry < today:
        status = "expired"
    elif (expiry - today).days <= 30:
        status = "expiring-soon"
    else:
        status = "valid"
    return ResourceCertificationDesktopDto(
        id=certification.id,
        resource_id=certification.resource_id,
        certification_code=certification.certification_code,
        certification_name=certification.certification_name,
        issued_date=issued.isoformat() if issued else None,
        expiry_date=expiry.isoformat() if expiry else None,
        issuing_body=certification.issuing_body or "",
        notes=certification.notes or "",
        cert_status=status,
    )


__all__ = ["serialize_certification"]
