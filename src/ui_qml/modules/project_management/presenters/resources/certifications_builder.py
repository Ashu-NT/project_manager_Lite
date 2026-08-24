from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
    ResourceAddCertificationCommand,
    ResourceRemoveCertificationCommand,
    ResourceUpdateCertificationCommand,
)
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceCertificationViewModel,
)

from .validation import optional_text, require_text

def build_certifications_state(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
) -> tuple[ResourceCertificationViewModel, ...]:
    if not resource_id:
        return ()
    certs = desktop_api.list_resource_certifications(resource_id)
    return tuple(
        ResourceCertificationViewModel(
            id=c.id,
            certification_code=c.certification_code,
            certification_name=c.certification_name,
            issued_date=c.issued_date or "",
            expiry_date=c.expiry_date or "",
            certificate_number=c.certificate_number,
            issuer=c.issuer,
            notes=c.notes,
            cert_status=c.cert_status,
            cert_status_label=c.cert_status_label,
            version=c.version,
        )
        for c in certs
    )

def add_certification(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    payload: dict[str, Any],
) -> None:
    command = ResourceAddCertificationCommand(
        resource_id=resource_id,
        certification_code=require_text(payload, "certCode", "Certification code is required."),
        certification_name=optional_text(payload, "certName") or payload.get("certCode", ""),
        issued_date=optional_text(payload, "issuedDate"),
        expiry_date=optional_text(payload, "expiryDate"),
        certificate_number=optional_text(payload, "certificateNumber") or "",
        issuer=optional_text(payload, "issuer") or "",
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.add_resource_certification(command)

def remove_certification(
    desktop_api: ProjectManagementResourcesDesktopApi,
    cert_id: str,
    expected_version: int,
) -> None:
    normalized = (cert_id or "").strip()
    if not normalized:
        raise ValueError("Certification ID is required.")
    desktop_api.remove_resource_certification(
        ResourceRemoveCertificationCommand(
            cert_id=normalized,
            expected_version=expected_version,
        )
    )


def update_certification(
    desktop_api: ProjectManagementResourcesDesktopApi,
    payload: dict[str, Any],
) -> None:
    desktop_api.update_resource_certification(
        ResourceUpdateCertificationCommand(
            cert_id=require_text(payload, "certId", "Certification ID is required."),
            expected_version=int(payload.get("expectedVersion", 0) or 0),
            certification_code=require_text(
                payload, "certCode", "Certification code is required."
            ),
            certification_name=optional_text(payload, "certName")
            or payload.get("certCode", ""),
            issued_date=optional_text(payload, "issuedDate"),
            expiry_date=optional_text(payload, "expiryDate"),
            certificate_number=optional_text(payload, "certificateNumber") or "",
            issuer=optional_text(payload, "issuer") or "",
            notes=optional_text(payload, "notes") or "",
        )
    )
