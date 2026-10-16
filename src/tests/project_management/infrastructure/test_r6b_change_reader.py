from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent
from sqlalchemy import event

from src.core.modules.project_management.api.desktop.financials import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lifecycle import (
    FinancialCreateBudgetVersionCommand,
    FinancialVersionedBudgetCommand,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lines import (
    FinancialAddBudgetLineCommand,
)
from src.core.modules.project_management.application.financials.configuration.dto.commands.cost_codes import (
    FinancialCreateCostCodeCommand,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.commands.change_draft import (
    FinancialCreateChangeCommand,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.commands.change_impacts import (
    FinancialChangeImpactCommand,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.commands.change_submission import (
    FinancialSubmitChangeCommand,
)
from src.core.modules.project_management.application.financials.forecasts.dto.commands.forecast_lifecycle import (
    FinancialVersionedForecastCommand,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_lifecycle import (
    TaskCreateCommand,
)
from src.core.modules.project_management.contracts.reads.financials.financial_changes.models.change_facts import (
    FinancialChangeImpactQuery,
    FinancialChangeRequestQuery,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.ui_qml.shell.qml_engine import create_qml_engine


@contextmanager
def _statement_count(session):
    statements: list[str] = []

    def before(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            statements.append(statement)

    event.listen(session.get_bind(), "before_cursor_execute", before)
    try:
        yield statements
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", before)


def _seed_changes(services):
    project = services["project_create"].create_project(
        ProjectCreateCommand(name="R6B Change Reader", financial_currency_code="USD")
    )
    boundary = services["finance_governance_commands"]
    query = services["financial_change_query"]
    code = boundary.cost_code(
        lambda handler: handler.create_cost_code(
            FinancialCreateCostCodeCommand(code="R6B-CHANGE", name="Governed change")
        )
    )
    _approve_finance_bases(services, project.id, code.id)
    task = services["task_lifecycle_commands"].create_task(
        TaskCreateCommand(
            project_id=project.id,
            name="Commission changed scope",
            start_date=date(2026, 9, 1),
            duration_days=5,
        )
    )
    result = boundary.financial_change(
        lambda handler: handler.create_change(
            FinancialCreateChangeCommand(
                project_id=project.id,
                title="Alpha approved scope",
                reason="Customer-approved scope increase",
                description="Governed commercial and schedule evidence.",
                effective_date="2026-09-01",
            )
        )
    )
    alpha = query.get_change(result.change_id)
    for impact_type, description, amount in (
        ("budget", "Increase approved budget", "125.2500"),
        ("forecast", "Increase forecast exposure", "80.5000"),
    ):
        boundary.financial_change(
            lambda handler: handler.add_impact(
                FinancialChangeImpactCommand(
                    change_id=alpha.id,
                    expected_change_version=alpha.row_version,
                    impact_type=impact_type,
                    description=description,
                    amount=amount,
                    cost_code_id=code.id,
                )
            )
        )
        alpha = query.get_change(alpha.id)
    boundary.financial_change(
        lambda handler: handler.add_impact(
            FinancialChangeImpactCommand(
                change_id=alpha.id,
                expected_change_version=alpha.row_version,
                impact_type="schedule",
                description="Move commissioning window",
                task_id=task.id,
                schedule_start="2026-09-08",
                schedule_finish="2026-09-11",
            )
        )
    )
    alpha = query.get_change(alpha.id)
    impacts = {item.impact_type.value: item for item in query.list_impacts(alpha.id)}
    boundary.financial_change_submission(
        lambda handler: handler.submit_change(
            FinancialSubmitChangeCommand(alpha.id, alpha.row_version)
        )
    )
    alpha = query.get_change(alpha.id)
    result = boundary.financial_change(
        lambda handler: handler.create_change(
            FinancialCreateChangeCommand(
                project_id=project.id,
                title="Zulu contingency",
                reason="Contingency evidence",
                effective_date="2026-10-01",
            )
        )
    )
    zulu = query.get_change(result.change_id)
    services["session"].expire_all()
    return (
        project,
        code,
        task,
        alpha,
        zulu,
        impacts["budget"],
        impacts["forecast"],
        impacts["schedule"],
    )


def _approve_finance_bases(services, project_id: str, cost_code_id: str) -> None:
    boundary = services["finance_governance_commands"]
    budget = boundary.budget_lifecycle(
        lambda handler: handler.create_budget(
            FinancialCreateBudgetVersionCommand(project_id, "R6B approved budget")
        )
    )
    boundary.budget_lines(
        lambda handler: handler.add_line(
            FinancialAddBudgetLineCommand(
                budget_id=budget.budget_id,
                expected_parent_version=budget.row_version,
                cost_code_id=cost_code_id,
                description="Approved scope base",
                amount="1000",
                currency_code="USD",
            )
        )
    )
    budget = services["budget_query"].get_budget(budget.budget_id)
    result = boundary.budget_lifecycle(
        lambda handler: handler.submit_budget(
            FinancialVersionedBudgetCommand(budget.id, budget.row_version)
        )
    )
    boundary.budget_approval(
        lambda handler: handler.approve_budget(
            result.budget_id, approved_by="admin", expected_version=result.row_version
        )
    )
    forecast = boundary.forecast_lifecycle(
        lambda handler: handler.create_forecast(
            project_id,
            name="R6B approved forecast",
            as_of_date=date(2026, 8, 28),
            generation_mode=ForecastGenerationMode.MANUAL,
            created_by="admin",
        )
    )
    boundary.forecast_lines(
        lambda handler: handler.add_line(
            forecast.id,
            cost_code_id=cost_code_id,
            description="Approved forecast base",
            amount=Decimal(900),
            source_kind=ForecastLineSourceKind.MANUAL,
            source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
            created_by="admin",
            expected_forecast_version=forecast.row_version,
        )
    )
    forecast = services["forecast_version_query"].get_forecast(forecast.id)
    result = boundary.forecast_lifecycle(
        lambda handler: handler.submit_forecast(
            FinancialVersionedForecastCommand(forecast.id, forecast.row_version)
        )
    )
    boundary.forecast_approval(
        lambda handler: handler.approve_forecast(
            result.forecast_id, approved_by="admin", expected_version=result.row_version
        )
    )


def test_change_reader_is_bounded_sorted_filtered_and_selection_is_explicit(services):
    project, _code, _task, alpha, zulu, *_impacts = _seed_changes(services)
    reader = services["finance_workspace_query"]._change_reader
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test change reader"
    )

    with _statement_count(services["session"]) as statements:
        page = reader.list_changes(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project.id,
            request=FinancialChangeRequestQuery(
                page=1, page_size=1, sort_key="title", sort_direction="asc"
            ),
        )
    assert len(statements) == 2
    assert page.total == 2
    assert page.items[0].id == alpha.id
    assert page.items[0].impact_count == 3

    descending = reader.list_changes(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project.id,
        request=FinancialChangeRequestQuery(
            page=1, page_size=1, sort_key="title", sort_direction="desc"
        ),
    )
    assert descending.items[0].id == zulu.id
    pending = reader.list_changes(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project.id,
        request=FinancialChangeRequestQuery(
            search="approved scope",
            status="pending_approval",
            approval_status="pending",
        ),
    )
    assert pending.total == 1
    assert pending.items[0].id == alpha.id

    workspace = services["finance_workspace_query"].get_change_workspace(project.id)
    assert workspace.selected_change_id == ""
    assert workspace.selected_change is None
    assert workspace.impacts.items == ()


def test_selected_change_detail_and_typed_impacts_are_bounded(services):
    project, code, task, alpha, _zulu, budget, forecast, schedule = _seed_changes(
        services
    )
    reader = services["finance_workspace_query"]._change_reader
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test selected change"
    )

    with _statement_count(services["session"]) as detail_statements:
        detail = reader.get_change(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project.id,
            change_id=alpha.id,
        )
    with _statement_count(services["session"]) as impact_statements:
        impacts = reader.list_impacts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project.id,
            change_id=alpha.id,
            request=FinancialChangeImpactQuery(
                page=1, page_size=2, sort_key="title", sort_direction="asc"
            ),
        )
    assert len(detail_statements) == 1
    assert len(impact_statements) == 2
    assert detail is not None
    assert detail.approval_status.lower() == "pending"
    assert detail.approval_request_id
    assert detail.impact_count == 3
    assert detail.base_budget_is_current is True
    assert detail.base_forecast_is_current is True
    assert impacts.total == 3
    assert len(impacts.items) == 2

    all_impacts = reader.list_impacts(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project.id,
        change_id=alpha.id,
        request=FinancialChangeImpactQuery(page_size=10),
    )
    by_id = {item.id: item for item in all_impacts.items}
    assert by_id[budget.id].amount == Decimal("125.2500")
    assert by_id[budget.id].cost_code_id == code.id
    assert by_id[forecast.id].impact_type == "forecast"
    assert by_id[schedule.id].task_id == task.id
    assert by_id[schedule.id].schedule_start == date(2026, 9, 8)
    assert by_id[schedule.id].schedule_finish == date(2026, 9, 11)
    assert by_id[schedule.id].amount == Decimal(0)

    schedule_only = reader.list_impacts(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project.id,
        change_id=alpha.id,
        request=FinancialChangeImpactQuery(
            search="commission", impact_type="schedule", applied_state="not_applied"
        ),
    )
    assert schedule_only.total == 1
    assert schedule_only.items[0].id == schedule.id


def test_change_reader_denies_wrong_parent_scope_and_api_preserves_decimal(services):
    project, _code, _task, alpha, _zulu, budget, *_ = _seed_changes(services)
    other_project = services["project_create"].create_project(
        ProjectCreateCommand(name="R6B Other Project", financial_currency_code="USD")
    )
    query = services["finance_workspace_query"]
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test change scope"
    )
    assert (
        query._change_reader.get_change(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=other_project.id,
            change_id=alpha.id,
        )
        is None
    )
    foreign_children = query._change_reader.list_impacts(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=other_project.id,
        change_id=alpha.id,
        request=FinancialChangeImpactQuery(),
    )
    assert foreign_children.total == 0

    dto = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=query
    ).get_change_workspace(project.id, selected_change_id=alpha.id)
    assert dto.selected_change_id == alpha.id
    impact = next(item for item in dto.impacts.items if item.id == budget.id)
    assert isinstance(impact.amount, Decimal)
    assert impact.amount == Decimal("125.2500")
    assert dto.selected_change is not None
    assert dto.selected_change.approval_request_id


def test_change_workspace_requires_finance_read_permission(services):
    project, *_ = _seed_changes(services)
    session = services["user_session"]
    session.set_principal(
        UserSessionPrincipal(
            user_id="change-reader-without-finance",
            username="change-reader-without-finance",
            display_name="No Finance Reader",
            role_names=frozenset(),
            permissions=frozenset(),
            active_tenant_id=session.stored_active_tenant_id(),
            active_organization_id=session.stored_active_organization_id(),
        )
    )
    with pytest.raises(BusinessRuleError) as exc:
        services["finance_workspace_query"].get_change_workspace(project.id)
    assert exc.value.code == "PERMISSION_DENIED"


@pytest.mark.parametrize(
    ("width", "height"),
    ((1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)),
)
def test_change_master_detail_loads_at_supported_viewports(
    qapp, width: int, height: int
):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        b"""
import QtQuick
import workspaces.financials.financial_changes.sections 1.0
Window {
    visible: true
    FinancialsChangeSection {
        id: section
        objectName: "changeSection"
        anchors.fill: parent
        changes: ({"items": [{"id": "change-1"}], "page": 1, "pageSize": 50, "total": 1})
        selectedChangeId: "change-1"
        selectedChange: ({"id": "change-1", "title": "Approved scope", "fields": []})
        impacts: ({"items": [{"id": "impact-1"}], "page": 1, "pageSize": 50, "total": 1})
    }
}
""",
        QUrl(),
    )
    assert component.isReady(), [error.toString() for error in component.errors()]
    window = component.create()
    assert window is not None
    window.setProperty("width", width)
    window.setProperty("height", height)
    window.show()
    qapp.processEvents()
    section = window.findChild(QObject, "changeSection")
    master = window.findChild(QObject, "financialChangesTable")
    impacts = window.findChild(QObject, "financialChangeImpactsTable")
    assert section is not None
    assert master is not None and float(master.property("width")) >= width - 2
    assert impacts is not None and float(impacts.property("width")) >= width - 2
    window.deleteLater()


def test_change_qml_contract_keeps_authoritative_tables_and_governed_actions():
    source = (
        "src/ui_qml/modules/project_management/qml/workspaces/financials/financial_changes/sections/"
        "FinancialsChangeSection.qml"
    )
    text = open(source, encoding="utf-8").read()
    assert text.count('sortingMode: "server"') == 2
    assert "changeSelected" in text
    assert "impactFiltersRequested" in text
    assert "requestCreateRequested" in text
    assert "requestEditRequested" in text
    assert "impactCreateRequested" in text
    assert "impactEditRequested" in text
    assert "impactRemoveRequested" in text
    assert "requestLifecycleRequested" in text
    assert "model.append" not in text
    assert "model.remove" not in text
