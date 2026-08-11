from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.core.modules.project_management.api.desktop.financials import (
    FinancialCreateManualActualCommand,
    FinancialDecideActualCommand,
    FinancialPostActualCommand,
    FinancialUpdateActualDraftCommand,
    FinancialVersionedActualCommand,
    ProjectManagementFinancialsDesktopApi,
)
from src.core.platform.common.exceptions import BusinessRuleError


def _build_api(services) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        project_service=services["project_service"],
        task_service=services["task_service"],
        financial_configuration_service=services["financial_configuration_service"],
        cost_entry_service=services["cost_entry_service"],
    )


def _setup_project(services):
    organization = services["organization_service"].get_active_organization()
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

    options = api.get_manual_actual_options(
        project.id, effective_on=date(2026, 1, 12)
    )
    assert options.currency_code == organization.base_currency
    assert [(item.value, item.label) for item in options.cost_codes] == [
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
