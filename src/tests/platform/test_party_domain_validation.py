from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.domain.master_data.party import Party, PartyType


class _FakeSession:
    def __init__(self) -> None:
        self.commit_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        return None


class _FakeTenantContext:
    def __init__(self, organization: Organization) -> None:
        self._organization = organization

    def get_active_organization(self) -> Organization:
        return self._organization


class _FakeEnterpriseAuditService:
    def record(self, **kwargs) -> None:
        return None


class _FakePartyUnitOfWork:
    def __init__(self, party_repo: "_FakePartyRepo", enterprise_audit_service) -> None:
        self.parties = party_repo
        self._enterprise_audit_service = enterprise_audit_service

    def __enter__(self) -> "_FakePartyUnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def commit(self) -> None:
        return None

    def record_event(self, event) -> None:
        return None


class _FakePartyUnitOfWorkFactory:
    def __init__(self, party_repo: "_FakePartyRepo", enterprise_audit_service) -> None:
        self._party_repo = party_repo
        self._enterprise_audit_service = enterprise_audit_service

    def create(self, *, context) -> _FakePartyUnitOfWork:
        return _FakePartyUnitOfWork(self._party_repo, self._enterprise_audit_service)


class _FakePartyRepo:
    def __init__(self) -> None:
        self._rows: dict[str, Party] = {}

    def add(self, party: Party) -> None:
        self._rows[party.id] = party

    def update(self, party: Party) -> None:
        if party.id not in self._rows:
            raise NotFoundError("Party not found.", code="PARTY_NOT_FOUND")
        party.version += 1
        self._rows[party.id] = party

    def get(self, party_id: str) -> Party | None:
        return self._rows.get(party_id)

    def get_by_code(self, organization_id: str, party_code: str) -> Party | None:
        for row in self._rows.values():
            if row.organization_id == organization_id and row.party_code == party_code:
                return row
        return None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Party]:
        rows = [row for row in self._rows.values() if row.organization_id == organization_id]
        if active_only is not None:
            rows = [row for row in rows if row.is_active is bool(active_only)]
        return sorted(rows, key=lambda row: row.party_name)


def _make_organization() -> Organization:
    return Organization.create(
        organization_code="default",
        display_name="Default Organization",
        timezone_name="UTC",
        base_currency="EUR",
        tenant_id="tenant-1",
    )


def _make_service(monkeypatch: pytest.MonkeyPatch) -> PartyService:
    monkeypatch.setattr(
        "src.core.platform.application.master_data.party.party_service.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.platform.application.master_data.party.party_service.require_any_permission",
        lambda *args, **kwargs: None,
    )
    party_repo = _FakePartyRepo()
    enterprise_audit_service = _FakeEnterpriseAuditService()
    return PartyService(
        session=_FakeSession(),
        party_repo=party_repo,
        organization_repo=object(),
        user_session=object(),
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=_FakeTenantContext(_make_organization()),
        uow_factory=_FakePartyUnitOfWorkFactory(party_repo, enterprise_audit_service),
    )


def test_party_dto_normalizes_and_validates_fields():
    party = Party.create(
        organization_id="  org-1  ",
        party_code="  sup-001  ",
        party_name="  North Supply  ",
        party_type="supplier",
        legal_name="  North Supply GmbH  ",
        contact_name="  Jane Doe  ",
        email="  SALES@EXAMPLE.COM  ",
        phone="  +49-555-0101  ",
        country="  Germany  ",
        city="  Berlin  ",
        address_line_1="  Street 1  ",
        address_line_2="  Floor 2  ",
        postal_code="  10115  ",
        website="  https://example.com  ",
        tax_registration_number="  TAX-001  ",
        external_reference="  EXT-001  ",
        notes="  Preferred vendor  ",
    )

    assert party.organization_id == "org-1"
    assert party.party_code == "SUP-001"
    assert party.party_name == "North Supply"
    assert party.party_type is PartyType.SUPPLIER
    assert party.legal_name == "North Supply GmbH"
    assert party.contact_name == "Jane Doe"
    assert party.email == "sales@example.com"
    assert party.phone == "+49-555-0101"
    assert party.country == "Germany"
    assert party.city == "Berlin"
    assert party.address_line_1 == "Street 1"
    assert party.address_line_2 == "Floor 2"
    assert party.postal_code == "10115"
    assert party.website == "https://example.com"
    assert party.tax_registration_number == "TAX-001"
    assert party.external_reference == "EXT-001"
    assert party.notes == "Preferred vendor"
    assert party.created_at is not None
    assert party.updated_at is not None

    with pytest.raises(ValidationError) as exc_org:
        Party.create(
            organization_id=" ",
            party_code="SUP-001",
            party_name="Valid",
        )
    assert exc_org.value.code == "PARTY_ORGANIZATION_REQUIRED"

    with pytest.raises(ValidationError) as exc_type:
        Party.create(
            organization_id="org-1",
            party_code="SUP-001",
            party_name="Valid",
            party_type="invalid",
        )
    assert exc_type.value.code == "PARTY_TYPE_INVALID"


def test_party_service_uses_entity_validation_and_final_state(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)

    created = service.create_party(
        party_code=" sup-001 ",
        name="  North Supply  ",
        party_type="supplier",
        legal_name="  North Supply GmbH  ",
        email="  SALES@EXAMPLE.COM  ",
        phone="  +49-555-0101  ",
        country="  Germany  ",
        city="  Berlin  ",
        notes="  Preferred vendor  ",
    )

    assert created.party_code == "SUP-001"
    assert created.party_name == "North Supply"
    assert created.party_type is PartyType.SUPPLIER
    assert created.legal_name == "North Supply GmbH"
    assert created.email == "sales@example.com"
    assert created.phone == "+49-555-0101"
    assert created.country == "Germany"
    assert created.city == "Berlin"
    assert created.notes == "Preferred vendor"

    resolved = service.find_party_by_code(" sup-001 ")
    assert resolved is not None
    assert resolved.id == created.id

    updated = service.update_party(
        created.id,
        party_code=" ven-002 ",
        party_name="  North Services  ",
        party_type="service_provider",
        email="",
        phone="  +49-555-0102  ",
        city="  Hamburg  ",
        expected_version=created.version,
    )

    assert updated.party_code == "VEN-002"
    assert updated.party_name == "North Services"
    assert updated.party_type is PartyType.SERVICE_PROVIDER
    assert updated.email == ""
    assert updated.phone == "+49-555-0102"
    assert updated.city == "Hamburg"

    search_rows = service.search_parties(search_text="services", party_type="service_provider")
    assert [row.id for row in search_rows] == [updated.id]

    with pytest.raises(ValidationError) as exc_duplicate:
        service.create_party(
            party_code=" ven-002 ",
            party_name="Duplicate Vendor",
        )
    assert exc_duplicate.value.code == "PARTY_CODE_EXISTS"
