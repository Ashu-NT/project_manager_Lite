from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.core.modules.project_management.api.desktop.financials import (
    FinancialCreateManualActualCommand,
    FinancialDecideActualCommand,
    FinancialPostActualCommand,
    FinancialReverseActualCommand,
    FinancialUpdateActualDraftCommand,
    FinancialVersionedActualCommand,
    ProjectManagementFinancialsDesktopApi,
)
from src.core.platform.common.exceptions import BusinessRuleError


def _build_api(services) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"],
        financial_configuration_service=services["financial_configuration_service"],
        cost_entry_service=services["cost_entry_service"],
    )


def _setup_project(services):
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "Desktop actual cutover",
        financial_currency_code=organization.base_currency,
    )
    task = services["task_service"].create_task(
        project.id,
        "Commission equipment",
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="ACTUAL-MANUAL",
        name="Manual actuals",
    )
    services["financial_period_service"].create_period(
        code="FY26-P01",
        name="January 2026",
        fiscal_year=2026,
        period_number=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    return organization, project, task, cost_code


def test_desktop_cutover_creates_canonical_draft_and_preserves_posted_immutability(
    services,
) -> None:
    organization, project, task, cost_code = _setup_project(services)
    api = _build_api(services)

    defaults = api.get_manual_actual_defaults(project.id)
    cost_codes = api.search_manual_actual_cost_codes(
        project.id,
        search="ACTUAL-MANUAL",
        effective_on=date(2026, 1, 12),
    )
    assert defaults.currency_code == organization.base_currency
    assert [(item.value, item.label) for item in cost_codes.items] == [
        (cost_code.id, "ACTUAL-MANUAL - Manual actuals")
    ]

    create = FinancialCreateManualActualCommand(
        project_id=project.id,
        command_id="desktop-command-1",
        description="Field commissioning expense",
        amount=Decimal("125.50"),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 12),
        cost_code_id=cost_code.id,
        task_id=task.id,
    )
    draft = api.create_manual_actual(create)
    replay = api.create_manual_actual(create)
    assert replay.id == draft.id
    assert draft.status == "draft"
    assert draft.amount == "125.50"
    assert draft.can_edit and draft.can_delete and draft.can_submit

    updated = api.update_actual_draft(
        FinancialUpdateActualDraftCommand(
            entry_id=draft.id,
            expected_version=draft.row_version,
            description="Field commissioning expense corrected",
            amount=Decimal("130.00"),
            currency_code=organization.base_currency,
            transaction_date=date(2026, 1, 13),
            cost_code_id=cost_code.id,
            task_id=task.id,
        )
    )
    submitted = api.submit_actual(
        FinancialVersionedActualCommand(updated.id, updated.row_version)
    )
    approved = api.approve_actual(
        FinancialDecideActualCommand(submitted.id, submitted.row_version)
    )
    assert approved.outcome == "applied"
    posted = api.post_actual(
        FinancialPostActualCommand(
            approved.entry_id,
            approved.row_version,
            posting_date=date(2026, 1, 13),
        )
    )
    assert posted.status == "posted"
    assert not posted.can_edit and not posted.can_delete
    assert posted.can_reverse

    with pytest.raises(BusinessRuleError):
        api.delete_actual_draft(
            FinancialVersionedActualCommand(posted.id, posted.row_version)
        )

    page = api.list_cost_entries(project.id)
    assert page.total == 1
    assert page.items[0].id == posted.id
    assert page.items[0].source_label == "Manual entry"

    reversed_command_id = "desktop-command-1-reversal"
    reversal = api.reverse_actual(
        FinancialReverseActualCommand(
            entry_id=posted.id,
            expected_version=posted.row_version,
            command_id=reversed_command_id,
            posting_date=date(2026, 1, 14),
            reason="Field commissioning expense corrected after reversal.",
        )
    )
    assert reversal.status == "posted"
    assert reversal.entry_kind == "reversal"
    # A reversal entry is itself the correction — it cannot be reversed again.
    assert reversal.can_reverse is False

    page_after_reversal = api.list_cost_entries(project.id)
    assert page_after_reversal.total == 2
    reversed_original = next(
        item for item in page_after_reversal.items if item.id == posted.id
    )
    assert reversed_original.status == "reversed"
    assert reversed_original.can_reverse is False


def test_desktop_reject_actual_returns_submitted_entry_to_draft(services) -> None:
    organization, project, task, cost_code = _setup_project(services)
    api = _build_api(services)

    draft = api.create_manual_actual(
        FinancialCreateManualActualCommand(
            project_id=project.id,
            command_id="desktop-command-reject-1",
            description="Awaiting approval",
            amount=Decimal("42.00"),
            currency_code=organization.base_currency,
            transaction_date=date(2026, 1, 12),
            cost_code_id=cost_code.id,
            task_id=task.id,
        )
    )
    submitted = api.submit_actual(
        FinancialVersionedActualCommand(draft.id, draft.row_version)
    )
    assert submitted.can_approve

    rejected = api.reject_actual(
        FinancialDecideActualCommand(
            submitted.id, submitted.row_version, notes="Wrong cost code."
        )
    )

    assert rejected.status == "draft"
    assert rejected.can_edit and rejected.can_delete and rejected.can_submit
    assert not rejected.can_approve


def test_legacy_combined_write_adapters_and_import_contract_are_deleted() -> None:
    root = Path(__file__).resolve().parents[2]
    production_files = (
        root / "core/modules/project_management/api/desktop/financials/api.py",
        root / "ui_qml/modules/project_management/presenters/financials/command_handler.py",
        root / "ui_qml/modules/project_management/controllers/financials/financials_mutation_mixin.py",
        root / "ui_qml/modules/project_management/qml/workspaces/financials/FinancialsWorkspacePage.qml",
    )
    forbidden = (
        "create_cost_item",
        "update_cost_item",
        "delete_cost_item",
        "createCostItem",
        "updateCostItem",
        "deleteCostItem",
    )
    for path in production_files:
        text = path.read_text(encoding="utf-8")
        assert all(token not in text for token in forbidden)

    import_service = (
        root
        / "core/modules/project_management/infrastructure/importers/services/data_import_service.py"
    ).read_text(encoding="utf-8")
    assert '"costs"' not in import_service
    assert not (
        root
        / "core/modules/project_management/application/financials/costs/commands/cost_lifecycle.py"
    ).exists()
