from __future__ import annotations

from src.core.platform.domain.data_operations.importing import (
    ImportFieldSpec,
    ImportPreviewRow,
    ImportSourceRow,
)
from src.core.platform.domain.master_data.party import (
    PartyRole,
    PartyType,
)

_SITE_FIELDS: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec(key="site_code", label="Site Code", required=True),
    ImportFieldSpec(key="name", label="Name", required=True),
    ImportFieldSpec(key="description", label="Description"),
    ImportFieldSpec(key="country", label="Country"),
    ImportFieldSpec(key="region", label="Region"),
    ImportFieldSpec(key="city", label="City"),
    ImportFieldSpec(key="address_line_1", label="Address Line 1"),
    ImportFieldSpec(key="address_line_2", label="Address Line 2"),
    ImportFieldSpec(key="postal_code", label="Postal Code"),
    ImportFieldSpec(key="timezone", label="Timezone"),
    ImportFieldSpec(key="currency_code", label="Currency Code"),
    ImportFieldSpec(key="site_type", label="Site Type"),
    # Status is the ONE lifecycle column -- active/inactive/archived (see
    # SITE_STATUS_* / normalize_site_status). No separate is_active column;
    # a site's activation state is fully implied by status.
    ImportFieldSpec(key="status", label="Status"),
    ImportFieldSpec(key="default_calendar_id", label="Default Calendar"),
    ImportFieldSpec(key="default_language", label="Default Language"),
    ImportFieldSpec(key="notes", label="Notes"),
)

_PARTY_FIELDS: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec(key="party_code", label="Party Code", required=True),
    ImportFieldSpec(key="party_name", label="Party Name", required=True),
    # party_type is now the ORGANIZATION/INDIVIDUAL identity axis; a legacy
    # export's party_type carrying a role token (SUPPLIER, VENDOR, ...) is
    # still accepted on import and folded into `roles` instead -- see
    # _parse_optional_party_type/_parse_legacy_party_type_role.
    ImportFieldSpec(key="party_type", label="Party Type"),
    ImportFieldSpec(key="roles", label="Roles"),
    ImportFieldSpec(key="legal_name", label="Legal Name"),
    ImportFieldSpec(key="contact_name", label="Contact Name"),
    ImportFieldSpec(key="email", label="Email"),
    ImportFieldSpec(key="phone", label="Phone"),
    ImportFieldSpec(key="country", label="Country"),
    ImportFieldSpec(key="city", label="City"),
    ImportFieldSpec(key="address_line_1", label="Address Line 1"),
    ImportFieldSpec(key="address_line_2", label="Address Line 2"),
    ImportFieldSpec(key="postal_code", label="Postal Code"),
    ImportFieldSpec(key="website", label="Website"),
    # registration_number carries a legacy export's tax_registration_number
    # column forward on import (see _parse_party_payload); exports only ever
    # emit the new canonical columns.
    ImportFieldSpec(key="registration_number", label="Registration Number"),
    ImportFieldSpec(key="tax_identifier", label="Tax Identifier"),
    ImportFieldSpec(key="external_reference", label="External Reference"),
    # status is the real lifecycle column; a legacy export's is_active
    # boolean column is still accepted on import -- see _reconcile_party_status.
    ImportFieldSpec(key="status", label="Status"),
    ImportFieldSpec(key="notes", label="Notes"),
)


def _text(value: str | None) -> str:
    return str(value or "").strip()


def _optional_text(value: str | None) -> str | None:
    normalized = _text(value)
    return normalized or None


def _parse_optional_bool(value: str | None) -> bool | None:
    normalized = _text(value).lower()
    if not normalized:
        return None
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError("Value must be a boolean token such as true/false or yes/no.")


_LEGACY_PARTY_TYPE_ROLE_TOKENS = {
    "SUPPLIER",
    "MANUFACTURER",
    "VENDOR",
    "CONTRACTOR",
    "SERVICE_PROVIDER",
    "CUSTOMER",
}


def _parse_optional_party_type(value: str | None) -> PartyType | None:
    normalized = _text(value).upper()
    if not normalized or normalized in _LEGACY_PARTY_TYPE_ROLE_TOKENS or normalized == "GENERAL":
        return None
    return PartyType(normalized)


def _parse_legacy_party_type_role(value: str | None) -> PartyRole | None:
    """A pre-refactor export's party_type column could carry a role token
    (SUPPLIER, VENDOR, ...) rather than an identity type -- fold it into
    roles instead of rejecting the column outright."""
    normalized = _text(value).upper()
    if normalized in _LEGACY_PARTY_TYPE_ROLE_TOKENS:
        return PartyRole(normalized)
    return None



def preview_error_row(row: ImportSourceRow, message: str) -> ImportPreviewRow:
    return ImportPreviewRow(
        line_no=row.line_no,
        status="ERROR",
        action="SKIP",
        message=message,
        row=dict(row.values),
    )

