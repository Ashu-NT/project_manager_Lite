from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.risk.register_service import RegisterService
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError


class _FakeSession:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class _FakeProjectRepo:
    def __init__(self, project_ids: list[str] | None = None) -> None:
        self._projects = {
            project_id: SimpleNamespace(id=project_id)
            for project_id in (project_ids or [])
        }

    def get(self, project_id: str):
        return self._projects.get(project_id)


class _FakeRegisterRepo:
    def __init__(self) -> None:
        self._entries: dict[str, RegisterEntry] = {}

    def add(self, entry: RegisterEntry) -> None:
        self._entries[entry.id] = entry

    def get(self, entry_id: str) -> RegisterEntry | None:
        return self._entries.get(entry_id)

    def update(self, entry: RegisterEntry) -> None:
        if entry.id not in self._entries:
            raise NotFoundError("Register entry not found.", code="REGISTER_ENTRY_NOT_FOUND")
        entry.version += 1
        self._entries[entry.id] = entry

    def delete(self, entry_id: str) -> None:
        self._entries.pop(entry_id, None)

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> list[RegisterEntry]:
        return [
            entry
            for entry in self._entries.values()
            if (project_id is None or entry.project_id == project_id)
            and (entry_type is None or entry.entry_type == entry_type)
            and (status is None or entry.status == status)
            and (severity is None or entry.severity == severity)
        ]


def _make_service(monkeypatch: pytest.MonkeyPatch, *, project_ids: list[str] | None = None) -> RegisterService:
    monkeypatch.setattr(
        "src.core.modules.project_management.application.risk.commands.register_lifecycle.require_permission",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.risk.commands.register_lifecycle.require_project_permission",
        lambda *args, **kwargs: None,
    )
    return RegisterService(
        session=_FakeSession(),
        project_repo=_FakeProjectRepo(project_ids or ["proj-1"]),
        register_repo=_FakeRegisterRepo(),
        user_session=object(),
    )


def test_register_entry_dto_normalizes_and_validates_fields():
    entry = RegisterEntry.create(
        "  proj-1  ",
        entry_type="risk",
        title="  Supplier Delay  ",
        code="  reg-manual-1  ",
        description="  Long lead electrical package.  ",
        severity="high",
        status="in_progress",
        owner_name="  Lead Planner  ",
        due_date=date(2026, 6, 1),
        impact_summary="  Commissioning could slip.  ",
        response_plan="  Expedite vendor review.  ",
    )

    assert entry.project_id == "proj-1"
    assert entry.entry_type == RegisterEntryType.RISK
    assert entry.title == "Supplier Delay"
    assert entry.code == "reg-manual-1"
    assert entry.description == "Long lead electrical package."
    assert entry.severity == RegisterEntrySeverity.HIGH
    assert entry.status == RegisterEntryStatus.IN_PROGRESS
    assert entry.owner_name == "Lead Planner"
    assert entry.due_date == date(2026, 6, 1)
    assert entry.impact_summary == "Commissioning could slip."
    assert entry.response_plan == "Expedite vendor review."
    assert entry.created_at is not None
    assert entry.updated_at is not None


def test_register_entry_dto_rejects_invalid_local_fields():
    with pytest.raises(ValidationError) as exc_project:
        RegisterEntry.create(
            " ",
            entry_type=RegisterEntryType.RISK,
            title="Valid",
        )
    assert exc_project.value.code == "REGISTER_PROJECT_REQUIRED"

    with pytest.raises(ValidationError) as exc_title:
        RegisterEntry.create(
            "proj-1",
            entry_type=RegisterEntryType.RISK,
            title=" ",
        )
    assert exc_title.value.code == "REGISTER_TITLE_EMPTY"

    with pytest.raises(ValidationError) as exc_type:
        RegisterEntry.create(
            "proj-1",
            entry_type="bad-type",
            title="Valid",
        )
    assert exc_type.value.code == "REGISTER_ENTRY_TYPE_INVALID"

    with pytest.raises(ValidationError) as exc_severity:
        RegisterEntry.create(
            "proj-1",
            entry_type=RegisterEntryType.RISK,
            title="Valid",
            severity="bad-severity",
        )
    assert exc_severity.value.code == "REGISTER_ENTRY_SEVERITY_INVALID"

    with pytest.raises(ValidationError) as exc_status:
        RegisterEntry.create(
            "proj-1",
            entry_type=RegisterEntryType.RISK,
            title="Valid",
            status="bad-status",
        )
    assert exc_status.value.code == "REGISTER_ENTRY_STATUS_INVALID"

    with pytest.raises(ValidationError) as exc_due_date:
        RegisterEntry.create(
            "proj-1",
            entry_type=RegisterEntryType.RISK,
            title="Valid",
            due_date="2026-06-01",
        )
    assert exc_due_date.value.code == "REGISTER_DUE_DATE_INVALID"


def test_register_service_update_validates_final_state(monkeypatch: pytest.MonkeyPatch):
    service = _make_service(monkeypatch)

    created = service.create_entry(
        "proj-1",
        entry_type="risk",
        title="  Supplier Delay  ",
        owner_name="  Lead Planner  ",
        code="REG-SUPP-1",
    )

    updated = service.update_entry(
        created.id,
        expected_version=created.version,
        title="  Supplier Delay Mitigated  ",
        description="  Final release note received.  ",
        severity="high",
        status="mitigated",
        owner_name="  Delivery Manager  ",
        due_date=None,
        impact_summary="  Residual freight risk remains.  ",
        response_plan="  Track shipment daily.  ",
        code="REG-MIT-1",
    )

    assert updated.title == "Supplier Delay Mitigated"
    assert updated.description == "Final release note received."
    assert updated.severity == RegisterEntrySeverity.HIGH
    assert updated.status == RegisterEntryStatus.MITIGATED
    assert updated.owner_name == "Delivery Manager"
    assert updated.due_date is None
    assert updated.impact_summary == "Residual freight risk remains."
    assert updated.response_plan == "Track shipment daily."
    assert updated.code == "REG-MIT-1"
    assert updated.version == 2

    reloaded = service._register_repo.get(created.id)
    assert reloaded is not None
    assert reloaded.code == "REG-MIT-1"

    with pytest.raises(ValidationError) as exc:
        service.update_entry(
            created.id,
            expected_version=updated.version,
            title=" ",
        )
    assert exc.value.code == "REGISTER_TITLE_EMPTY"
