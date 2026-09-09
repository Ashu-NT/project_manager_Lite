from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
    ProjectCostEntryService,
)
from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceReference,
    FinancialSourceType,
    financial_source_content_hash,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryKind,
    ProjectCostEntryStatus,
)
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.finance import Money


def _setup(services):
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "R6D-C Actual governance", financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="R6DC-ACTUAL", name="R6D-C Actual"
    )
    return organization, project, cost_code


def _draft(services):
    organization, project, cost_code = _setup(services)
    entry = services["cost_entry_service"].create_manual_entry(
        project_id=project.id,
        command_id="r6dc-manual",
        description="Governed manual actual",
        amount=Decimal("125.40"),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 9, 9),
        cost_code_id=cost_code.id,
    )
    return organization, project, cost_code, entry


def _become(services, user_id: str) -> None:
    session = services["user_session"]
    session.set_principal(
        replace(session.principal, user_id=user_id, username=user_id)
    )


def test_requester_cannot_approve_or_reject_even_with_both_permissions(services):
    _organization, _project, _cost_code, draft = _draft(services)
    service = services["cost_entry_service"]
    submitted = service.submit(draft.id, expected_version=draft.row_version)

    with pytest.raises(BusinessRuleError, match="cannot approve or reject") as approve_error:
        service.approve(submitted.id, expected_version=submitted.row_version)
    assert approve_error.value.code == "PROJECT_COST_ENTRY_SELF_DECISION_FORBIDDEN"

    with pytest.raises(BusinessRuleError, match="cannot approve or reject") as reject_error:
        service.reject(submitted.id, expected_version=submitted.row_version)
    assert reject_error.value.code == "PROJECT_COST_ENTRY_SELF_DECISION_FORBIDDEN"


def test_independent_decider_can_approve(services):
    _organization, _project, _cost_code, draft = _draft(services)
    service = services["cost_entry_service"]
    submitted = service.submit(draft.id, expected_version=draft.row_version)
    _become(services, "r6dc-independent-decider")

    result = service.approve(submitted.id, expected_version=submitted.row_version)

    assert result.outcome.value == "applied"


def test_desktop_actual_capabilities_are_permission_source_and_actor_aware(services):
    _organization, project, _cost_code, draft = _draft(services)
    desktop_api = build_desktop_api_registry(services).project_management_financials

    draft_page = desktop_api.list_cost_entries(project.id)
    draft_dto = draft_page.items[0]
    assert draft_page.can_create_manual_actual is True
    assert draft_dto.source_owned is False
    assert draft_dto.can_edit is True
    assert draft_dto.can_delete is True
    assert draft_dto.can_submit is True

    submitted = services["cost_entry_service"].submit(
        draft.id, expected_version=draft.row_version
    )
    submitted_dto = desktop_api.list_cost_entries(project.id).items[0]
    assert submitted_dto.can_approve is False
    assert submitted_dto.can_reject is False
    assert "cannot approve" in submitted_dto.read_only_reason

    _become(services, "r6dc-capability-decider")
    independent_dto = desktop_api.list_cost_entries(project.id).items[0]
    assert independent_dto.can_approve is True
    assert independent_dto.can_reject is True
    assert independent_dto.approval_action == "decide"
    assert independent_dto.row_version == submitted.row_version


def test_source_owned_entry_has_no_interactive_mutation_capability(services):
    organization, project, cost_code = _setup(services)
    actor_id = services["user_session"].principal.user_id
    payload = {"time_entry_id": "time-1", "hours": "2.0"}
    source = FinancialSourceReference(
        tenant_id=organization.tenant_id,
        organization_id=organization.id,
        project_id=project.id,
        source_module=FinancialSourceModule.PLATFORM_TIME,
        source_type=FinancialSourceType.TIME_ENTRY,
        source_id="time-1",
        source_revision="1",
        content_hash=financial_source_content_hash(payload),
        posting_purpose=FinancialPostingPurpose.LABOR_ACTUAL,
    )
    entry = ProjectCostEntry.create_draft(
        tenant_id=organization.tenant_id,
        organization_id=organization.id,
        project_id=project.id,
        description="Source-owned labor evidence",
        kind=ProjectCostEntryKind.ACTUAL,
        money=Money.of("20.00", organization.base_currency),
        transaction_date=date(2026, 9, 9),
        cost_code_id=cost_code.id,
        source=source,
        task_id=None,
        resource_id=None,
        actor_id=actor_id,
        occurred_at=datetime.now(timezone.utc),
    )
    capabilities = services["cost_entry_service"].capabilities_for(entry)
    assert capabilities.project_visible is True
    assert capabilities.is_manual is False
    assert not any(
        (
            capabilities.can_edit,
            capabilities.can_delete,
            capabilities.can_submit,
            capabilities.can_approve,
            capabilities.can_reject,
            capabilities.can_post,
            capabilities.can_reverse,
        )
    )

    with pytest.raises(BusinessRuleError) as source_error:
        ProjectCostEntryService._require_manual_interactive_entry(
            entry, operation="edit"
        )
    assert source_error.value.code == "PROJECT_COST_ENTRY_SOURCE_OWNED"


def test_actual_filters_are_server_owned_and_invalid_sources_fail_closed(services):
    _organization, project, _cost_code, draft = _draft(services)
    service = services["cost_entry_service"]

    rows, total = service.list_for_project(
        project.id,
        status=ProjectCostEntryStatus.DRAFT,
        source_module=FinancialSourceModule.PROJECT_MANAGEMENT,
    )
    assert total == 1
    assert [row.id for row in rows] == [draft.id]

    rows, total = service.list_for_project(
        project.id,
        source_module=FinancialSourceModule.PROCUREMENT,
    )
    assert rows == []
    assert total == 0

    with pytest.raises(ValidationError) as invalid:
        service.list_for_project(project.id, source_module="future-module")
    assert invalid.value.code == "PROJECT_COST_ENTRY_SOURCE_INVALID"


def test_cost_service_is_transaction_neutral_and_uses_scoped_savepoints_only():
    source = inspect.getsource(ProjectCostEntryService)
    assert ".commit(" not in source
    assert ".rollback(" not in source
    assert source.count("begin_nested()") == 2
