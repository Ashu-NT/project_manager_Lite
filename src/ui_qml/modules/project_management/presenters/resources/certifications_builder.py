from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
    ResourceAddCertificationCommand,
    ResourceRemoveCertificationCommand,
    ResourceUpdateCertificationCommand,
)
from .validation import optional_text, require_text


def build_certifications_page(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    **query,
) -> dict[str, object]:
    page = desktop_api.list_resource_certifications_page(resource_id, **query)
    return {
        "items": [
            {
                "id": cert.id,
                "title": cert.certification_name,
                "subtitle": cert.certification_code,
                "statusLabel": cert.cert_status_label,
                "metaText": cert.expiry_date or "No expiry",
                "certificationCode": cert.certification_code,
                "certificationName": cert.certification_name,
                "issuedDate": cert.issued_date or "",
                "expiryDate": cert.expiry_date or "",
                "certificateNumber": cert.certificate_number,
                "issuer": cert.issuer,
                "notes": cert.notes,
                "certStatus": cert.cert_status,
                "certStatusLabel": cert.cert_status_label,
                "version": cert.version,
            }
            for cert in page.items
        ],
        "total": page.filtered_total,
        "page": page.page,
        "pageSize": page.page_size,
        "sortKey": page.sort_key,
        "sortDirection": page.sort_direction,
    }

def add_certification(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    payload: dict[str, Any],
) -> None:
    command = ResourceAddCertificationCommand(
        resource_id=resource_id,
        certification_code=require_text(payload, "certCode", "Certification code is required."),
        certification_name=require_text(
            payload, "certName", "Certification name is required."
        ),
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
            certification_name=require_text(
                payload, "certName", "Certification name is required."
            ),
            issued_date=optional_text(payload, "issuedDate"),
            expiry_date=optional_text(payload, "expiryDate"),
            certificate_number=optional_text(payload, "certificateNumber") or "",
            issuer=optional_text(payload, "issuer") or "",
            notes=optional_text(payload, "notes") or "",
        )
    )
