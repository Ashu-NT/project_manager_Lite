from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


class PartyType(str, Enum):
    """What the Party IS -- an identity axis, never conflated with what
    business ROLE(S) it plays (see PartyRole below). Every Party created
    before this axis existed is ORGANIZATION (100% of real usage to date);
    INDIVIDUAL exists for a person counterparty (e.g. an external
    consultant) that has no legal_name/registration_number in the
    company sense."""

    ORGANIZATION = "ORGANIZATION"
    INDIVIDUAL = "INDIVIDUAL"


class PartyRole(str, Enum):
    """Business role(s) a Party plays -- additive, not mutually exclusive.
    A single Party may legitimately hold several of these at once (e.g. a
    Supplier that is also a Contractor); this replaces the old single-
    valued `party_type` enum, which conflated identity type and role and
    had no CUSTOMER value despite Customer already being a live, real
    consumer via PM's client_party_id/customer_party_id references. The
    old GENERAL value had no real meaning beyond "no role selected" and is
    not carried forward -- a Party with no roles is simply un-tagged."""

    SUPPLIER = "SUPPLIER"
    MANUFACTURER = "MANUFACTURER"
    VENDOR = "VENDOR"
    CONTRACTOR = "CONTRACTOR"
    SERVICE_PROVIDER = "SERVICE_PROVIDER"
    CUSTOMER = "CUSTOMER"


class PartyLifecycleStatus(str, Enum):
    """The sole lifecycle source of truth -- never a second `is_active`
    boolean alongside it. Only ACTIVE/INACTIVE exist today; deactivation
    means "not selectable for new operational links" (a new Project
    client, a new Commitment supplier) -- it never cascades to existing
    PM references, documents, or activity history, which all remain
    readable."""

    ACTIVE = "active"
    INACTIVE = "inactive"


def normalize_party_code(value: object) -> str:
    return normalize_required_text(
        value,
        message="Party code is required.",
        code="PARTY_CODE_REQUIRED",
    ).upper()


def normalize_party_name(value: object) -> str:
    return normalize_required_text(
        value,
        message="Party name is required.",
        code="PARTY_NAME_REQUIRED",
    )


def coerce_party_type(value: PartyType | str | None) -> PartyType:
    if isinstance(value, PartyType):
        return value
    raw = normalize_optional_text(value).upper() or PartyType.ORGANIZATION.value
    try:
        return PartyType(raw)
    except ValueError as exc:
        raise ValidationError("Party type is invalid.", code="PARTY_TYPE_INVALID") from exc


def _coerce_single_role(value: PartyRole | str) -> PartyRole:
    if isinstance(value, PartyRole):
        return value
    raw = normalize_optional_text(value).upper()
    try:
        return PartyRole(raw)
    except ValueError as exc:
        raise ValidationError(
            f"'{value}' is not a recognized party role.", code="PARTY_ROLE_INVALID"
        ) from exc


def coerce_party_roles(value: object) -> tuple[PartyRole, ...]:
    """Accepts None, a single role, or any iterable of roles/strings
    (comma-separated string also accepted for CSV import convenience).
    Deduplicates and returns roles in the enum's own declaration order,
    so persisted/serialized role sets are always deterministic regardless
    of input order."""
    if value is None or value == "":
        return ()
    if isinstance(value, (PartyRole, str)):
        items: list[object] = [part for part in str(value.value if isinstance(value, PartyRole) else value).split(",")]
    else:
        items = list(value)
    resolved = {_coerce_single_role(item) for item in items if str(item).strip()}
    return tuple(role for role in PartyRole if role in resolved)


def coerce_party_lifecycle_status(
    value: PartyLifecycleStatus | str | None,
) -> PartyLifecycleStatus:
    if isinstance(value, PartyLifecycleStatus):
        return value
    raw = normalize_optional_text(value).lower() or PartyLifecycleStatus.ACTIVE.value
    try:
        return PartyLifecycleStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Party lifecycle status is invalid.", code="PARTY_STATUS_INVALID"
        ) from exc


def normalize_party_email(value: object) -> str:
    return normalize_optional_text(value).lower()


def normalize_party_phone(value: object) -> str:
    return normalize_optional_text(value)


@validated_dataclass
class Party:
    id: str
    organization_id: str
    party_code: str
    party_name: str
    party_type: PartyType = PartyType.ORGANIZATION
    roles: tuple[PartyRole, ...] = ()
    legal_name: str = ""
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    country: str = ""
    city: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    postal_code: str = ""
    website: str = ""
    # Split from the old single `tax_registration_number` field -- a VAT/
    # tax identifier and a company registration number are two different
    # real-world identifiers that don't share a format; forcing them into
    # one field made neither reliable for a future Accounting/Procurement
    # consumer. `registration_number` carries the old field's values
    # forward (its original apparent intent); `tax_identifier` is new.
    registration_number: str = ""
    tax_identifier: str = ""
    external_reference: str = ""
    status: PartyLifecycleStatus = PartyLifecycleStatus.ACTIVE
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="PARTY_ORGANIZATION_REQUIRED",
        )

    @field_validator("party_code", mode="before")
    @classmethod
    def _validate_party_code(cls, value: object) -> str:
        return normalize_party_code(value)

    @field_validator("party_name", mode="before")
    @classmethod
    def _validate_party_name(cls, value: object) -> str:
        return normalize_party_name(value)

    @field_validator("party_type", mode="before")
    @classmethod
    def _validate_party_type(cls, value: PartyType | str | None) -> PartyType:
        return coerce_party_type(value)

    @field_validator("roles", mode="before")
    @classmethod
    def _validate_roles(cls, value: object) -> tuple[PartyRole, ...]:
        return coerce_party_roles(value)

    @field_validator(
        "legal_name",
        "contact_name",
        "country",
        "city",
        "address_line_1",
        "address_line_2",
        "postal_code",
        "website",
        "registration_number",
        "tax_identifier",
        "external_reference",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> str:
        return normalize_party_email(value)

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, value: object) -> str:
        return normalize_party_phone(value)

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value: PartyLifecycleStatus | str | None) -> PartyLifecycleStatus:
        return coerce_party_lifecycle_status(value)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_datetimes(cls, value: object) -> datetime | None:
        if value in (None, ""):
            return None
        if not isinstance(value, datetime):
            raise ValidationError(
                "Party timestamps must be valid datetimes.",
                code="PARTY_TIMESTAMP_INVALID",
            )
        return value

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = int(value if value not in (None, "") else 1)
        if resolved < 1:
            raise ValidationError(
                "Party version must be positive.",
                code="PARTY_VERSION_INVALID",
            )
        return resolved

    @property
    def is_active(self) -> bool:
        """Computed from status -- never a second persisted source of truth."""
        return self.status == PartyLifecycleStatus.ACTIVE

    @staticmethod
    def create(
        *,
        organization_id: str,
        party_code: str,
        party_name: str,
        party_type: PartyType | str = PartyType.ORGANIZATION,
        roles: object = (),
        legal_name: str = "",
        contact_name: str = "",
        email: str = "",
        phone: str = "",
        country: str = "",
        city: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        website: str = "",
        registration_number: str = "",
        tax_identifier: str = "",
        external_reference: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        notes: str = "",
    ) -> Party:
        # No `status`/`is_active` parameter -- every new Party starts
        # ACTIVE (PartyLifecycleStatus's own default). Use
        # activate_party/deactivate_party to change it afterward.
        now = datetime.now(timezone.utc)
        return Party(
            id=generate_id(),
            organization_id=organization_id,
            party_code=party_code,
            party_name=party_name,
            party_type=party_type,
            roles=roles,
            legal_name=legal_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            country=country,
            city=city,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            website=website,
            registration_number=registration_number,
            tax_identifier=tax_identifier,
            external_reference=external_reference,
            created_at=created_at or now,
            updated_at=updated_at or now,
            notes=notes,
            version=1,
        )

    @property
    def name(self) -> str:
        return self.party_name

    @name.setter
    def name(self, value: str) -> None:
        self.party_name = value


__all__ = [
    "Party",
    "PartyLifecycleStatus",
    "PartyRole",
    "PartyType",
    "coerce_party_lifecycle_status",
    "coerce_party_roles",
    "coerce_party_type",
    "normalize_party_code",
    "normalize_party_email",
    "normalize_party_name",
    "normalize_party_phone",
]
