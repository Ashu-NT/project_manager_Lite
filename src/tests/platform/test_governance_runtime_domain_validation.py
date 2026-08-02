from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.core.platform.approval.domain import ApprovalRequest, ApprovalStatus
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.platform_events.domain.platform_event import PlatformEvent
from src.core.platform.runtime_tracking.application.runtime_execution_service import RuntimeExecutionService
from src.core.platform.runtime_tracking.domain import RuntimeExecution
from src.core.platform.tenancy.domain.tenant import (
    TENANT_STATUS_ACTIVE,
    TENANT_STATUS_SUSPENDED,
    Tenant,
)


class _FakeRuntimeExecutionRepo:
    def __init__(self) -> None:
        self._rows: dict[str, RuntimeExecution] = {}

    def add(self, execution: RuntimeExecution) -> None:
        self._rows[execution.id] = execution

    def update(self, execution: RuntimeExecution) -> None:
        self._rows[execution.id] = execution

    def get(self, execution_id: str) -> RuntimeExecution | None:
        return self._rows.get(execution_id)

    def list_recent(
        self,
        *,
        limit: int = 200,
        module_code: str | None = None,
        status: str | None = None,
    ) -> list[RuntimeExecution]:
        rows = list(self._rows.values())
        if module_code is not None:
            rows = [row for row in rows if row.module_code == str(module_code).strip().lower()]
        if status is not None:
            rows = [row for row in rows if row.status == str(status).strip().upper()]
        return rows[:limit]


@dataclass
class _FakePrincipal:
    user_id: str
    username: str


@dataclass
class _FakeUserSession:
    principal: _FakePrincipal | None


class _FakeTenantContextService:
    def require_organization_context(self, *, operation_label: str):
        return type(
            "Context",
            (),
            {"tenant_id": "tenant-1", "organization_id": "org-1"},
        )()


def test_approval_request_dto_normalizes_and_validates_fields():
    request = ApprovalRequest.create(
        request_type="  COST.UPDATE  ",
        entity_type="  COST_ITEM  ",
        entity_id="  cost-1  ",
        project_id="  project-1  ",
        organization_id="  org-1  ",
        payload={"amount": 2500},
        requested_by_user_id="  user-1  ",
        requested_by_username="  Planner One  ",
    )

    assert request.request_type == "cost.update"
    assert request.entity_type == "cost_item"
    assert request.entity_id == "cost-1"
    assert request.project_id == "project-1"
    assert request.organization_id == "org-1"
    assert request.requested_by_user_id == "user-1"
    assert request.requested_by_username == "Planner One"

    request.status = "approved"
    request.decision_note = "  Approved for release  "
    request.decided_at = datetime(2026, 7, 1, 9, 30, 0)

    assert request.status == ApprovalStatus.APPROVED
    assert request.decision_note == "Approved for release"
    assert request.decided_at == datetime(2026, 7, 1, 9, 30, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError) as exc_payload:
        ApprovalRequest.create(
            request_type="baseline.create",
            entity_type="project_baseline",
            entity_id="baseline-1",
            project_id="project-1",
            payload=["not", "a", "dict"],
        )
    assert exc_payload.value.code == "APPROVAL_PAYLOAD_INVALID"


def test_tenant_dto_normalizes_and_validates_fields():
    tenant = Tenant.create(
        tenant_code="  acme-west  ",
        display_name="  Acme West  ",
        tenant_status="  SUSPENDED  ",
    )

    assert tenant.tenant_code == "ACME-WEST"
    assert tenant.display_name == "Acme West"
    assert tenant.tenant_status == TENANT_STATUS_SUSPENDED
    assert tenant.is_active is False

    tenant.tenant_status = " active "
    tenant.version = "2"

    assert tenant.tenant_status == TENANT_STATUS_ACTIVE
    assert tenant.is_active is True
    assert tenant.version == 2

    with pytest.raises(ValidationError) as exc_status:
        tenant.tenant_status = "disabled"
    assert exc_status.value.code == "TENANT_STATUS_INVALID"

    with pytest.raises(ValidationError) as exc_version:
        tenant.version = 0
    assert exc_version.value.code == "TENANT_VERSION_INVALID"


def test_platform_event_dto_normalizes_and_validates_fields():
    event = PlatformEvent.create(
        operation="  CREATE_TENANT  ",
        actor_user_id="  user-1  ",
        tenant_id="  tenant-1  ",
        resource_type="  TENANT  ",
        resource_id="  tenant-1  ",
        outcome="  SUCCESS  ",
        severity="  LOW  ",
        metadata={"step": "create"},
    )

    assert event.operation == "create_tenant"
    assert event.actor_user_id == "user-1"
    assert event.tenant_id == "tenant-1"
    assert event.resource_type == "tenant"
    assert event.resource_id == "tenant-1"
    assert event.outcome == "success"
    assert event.severity == "low"

    event.created_at = datetime(2026, 7, 2, 11, 0, 0)
    assert event.created_at == datetime(2026, 7, 2, 11, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError) as exc_metadata:
        event.metadata = ["bad-metadata"]
    assert exc_metadata.value.code == "PLATFORM_EVENT_METADATA_INVALID"


def test_runtime_execution_service_uses_entity_validation_for_updates():
    repo = _FakeRuntimeExecutionRepo()
    runtime = RuntimeExecutionService(
        runtime_execution_repo=repo,
        tenant_context_service=_FakeTenantContextService(),
        user_session=_FakeUserSession(
            principal=_FakePrincipal(
                user_id="  user-1  ",
                username="  Runtime Admin  ",
            )
        ),
    )

    input_path = Path("exports") / "source.csv"
    output_path = Path("exports") / "result.csv"
    execution = runtime.start_execution(
        operation_type="  REPORT  ",
        operation_key="  backlog.export  ",
        module_code="  PROJECT_MANAGEMENT  ",
        input_path=input_path,
        output_path=output_path,
        attempt_number="3",
    )

    assert execution.operation_type == "report"
    assert execution.tenant_id == "tenant-1"
    assert execution.organization_id == "org-1"
    assert execution.operation_key == "backlog.export"
    assert execution.module_code == "project_management"
    assert execution.status == "RUNNING"
    assert execution.input_path == str(input_path)
    assert execution.output_path == str(output_path)
    assert execution.requested_by_user_id == "user-1"
    assert execution.requested_by_username == "Runtime Admin"
    assert execution.attempt_number == 3

    completed = runtime.complete_execution(
        execution,
        output_file_name="  backlog.csv  ",
        output_media_type="  TEXT/CSV  ",
        output_metadata={"created_by": "system"},
        created_count="4",
        updated_count="1",
        error_count="0",
    )

    assert completed.output_file_name == "backlog.csv"
    assert completed.output_media_type == "text/csv"
    assert completed.output_metadata == {"created_by": "system"}
    assert completed.created_count == 4
    assert completed.updated_count == 1
    assert completed.error_count == 0
    assert completed.completed_at is not None

    with pytest.raises(ValidationError) as exc_attempt:
        completed.attempt_number = 0
    assert exc_attempt.value.code == "RUNTIME_EXECUTION_ATTEMPT_INVALID"

    with pytest.raises(ValidationError) as exc_count:
        completed.error_count = -1
    assert exc_count.value.code == "RUNTIME_EXECUTION_ERROR_COUNT_INVALID"
