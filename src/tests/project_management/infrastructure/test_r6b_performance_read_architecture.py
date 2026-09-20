from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent
from sqlalchemy import event

from src.core.modules.project_management.api.desktop.financials.models.performance import (
    FinancialEvmDto,
)
from src.core.modules.project_management.application.financials.performance_query import (
    ProjectFinancePerformanceQuery,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    CostPhasingFacts,
    CostPhasingPeriodFact,
    CostPhasingQuery,
)
from src.core.modules.project_management.infrastructure.persistence.orm.baseline import (
    BaselineTaskORM,
    ProjectBaselineORM,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials.sqlalchemy_finance_performance_reader import (
    SqlAlchemyFinancePerformanceReader,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.ui_qml.modules.project_management.presenters.financials.shared.destination_builder import (
    build_destination_state,
)
from src.ui_qml.shell.qml_engine import create_qml_engine


@contextmanager
def _statement_count(session):
    engine = session.get_bind()
    statements: list[str] = []

    def before_cursor(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor)


def _basis(**overrides):
    values = {
        "currency_code": "XAF",
        "approved_budget_revision": 2,
        "approved_budget_id": "budget-1",
        "approved_budget": Decimal(1_000),
        "approved_forecast_revision": 3,
        "approved_forecast_as_of": date(2026, 8, 1),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _query(monkeypatch, *, reader=None, evm=None, baseline=None):
    monkeypatch.setattr(
        "src.core.modules.project_management.application.financials.performance_query.require_permission",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "src.core.modules.project_management.application.financials.performance_query.require_project_permission",
        lambda *_args, **_kwargs: None,
    )
    context = MagicMock()
    context.require_active_scope_ids.return_value = SimpleNamespace(
        tenant_id="tenant-1", organization_id="org-1"
    )
    overview = MagicMock()
    overview.read_overview_facts.return_value = _basis()
    return ProjectFinancePerformanceQuery(
        performance_reader=reader or MagicMock(),
        overview_reader=overview,
        earned_value_authority=evm
        or SimpleNamespace(
            get_earned_value=MagicMock(
                return_value=SimpleNamespace(
                    availability="available",
                    unavailable_reason="",
                    baseline_id="baseline-1",
                    BAC=Decimal(900),
                    PV=Decimal(500),
                    EV=Decimal(600),
                    AC=Decimal(550),
                    CV=Decimal(50),
                    SV=Decimal(100),
                    CPI=Decimal("1.09"),
                    SPI=Decimal("1.20"),
                    ETC=Decimal(350),
                    EAC=Decimal(900),
                    VAC=Decimal(0),
                    TCPI_to_BAC=Decimal(1),
                    TCPI_to_EAC=Decimal(1),
                    notes="",
                )
            )
        ),
        baseline_variance_authority=baseline
        or MagicMock(list_baselines=MagicMock(return_value=[])),
        tenant_context_service=context,
    )


def test_performance_destination_loads_only_requested_subsection() -> None:
    api = MagicMock()
    api.get_performance_evm.return_value = FinancialEvmDto(
        project_id="project-1",
        as_of_date=date(2026, 8, 28),
        availability="baseline_unavailable",
        unavailable_reason="No approved baseline.",
    )

    state = build_destination_state(
        api,
        destination="performance",
        subsection="evm",
        selected_project_id="project-1",
        performance_as_of_date=date(2026, 8, 28),
    )

    assert state.evm_basis.empty_state == "No approved baseline."
    assert api.method_calls == [
        call.get_performance_evm(
            "project-1", as_of_date=date(2026, 8, 28), baseline_id=None
        )
    ]


def test_cost_phasing_query_preserves_scope_range_and_decimal_facts(
    monkeypatch,
) -> None:
    reader = MagicMock()
    reader.read_cost_phasing.return_value = CostPhasingFacts(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        as_of_date=date(2026, 8, 28),
        date_from=date(2026, 1, 1),
        date_to=date(2026, 8, 28),
        granularity="month",
        currency_code="XAF",
        periods=(
            CostPhasingPeriodFact(
                period_key="2026-08",
                period_start=date(2026, 8, 1),
                period_end=date(2026, 8, 31),
                planned_cost=Decimal("10.25"),
                open_commitment=Decimal("2.50"),
                posted_actual=Decimal("1.25"),
                forecast_cost=Decimal("4.00"),
                exposure=Decimal("7.75"),
                currency_code="XAF",
            ),
        ),
        approved_budget_id="budget-1",
        approved_budget_revision=2,
        approved_forecast_id="forecast-1",
        approved_forecast_revision=3,
        approved_forecast_as_of=date(2026, 8, 1),
    )
    query = _query(monkeypatch, reader=reader)

    result = query.get_cost_phasing(
        "project-1",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 8, 28),
        as_of_date=date(2026, 8, 15),
    )

    assert result.periods[0].planned_cost == Decimal("10.25")
    reader.read_cost_phasing.assert_called_once_with(
        tenant_id="tenant-1",
        organization_id="org-1",
        project_id="project-1",
        query=CostPhasingQuery(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 8, 28),
            granularity="month",
            as_of_date=date(2026, 8, 15),
        ),
    )


def test_evm_calculator_failure_is_contained_but_permission_denial_is_not(
    monkeypatch,
) -> None:
    calculator = MagicMock()
    calculator.get_earned_value.side_effect = NameError("known calculator defect")
    query = _query(monkeypatch, evm=calculator)

    unavailable = query.get_evm("project-1", as_of_date=date(2026, 8, 28))

    assert unavailable.availability == "calculator_error"
    assert unavailable.unavailable_reason == "Earned value is temporarily unavailable."

    calculator.get_earned_value.side_effect = BusinessRuleError(
        "finance.read denied", code="PERMISSION_DENIED"
    )
    with pytest.raises(BusinessRuleError, match="finance.read denied"):
        query.get_evm("project-1", as_of_date=date(2026, 8, 28))


def test_variance_metrics_consume_canonical_evm_and_approved_budget(
    monkeypatch,
) -> None:
    query = _query(monkeypatch)

    facts = query.get_variance("project-1", as_of_date=date(2026, 8, 28))
    metrics = {item.metric_code: item for item in facts.metrics}

    assert metrics["cost_variance"].value == Decimal(50)
    assert metrics["cost_variance"].favorability == "favorable"
    assert metrics["schedule_variance"].value == Decimal(100)
    assert metrics["schedule_variance"].favorability == "favorable"
    assert metrics["vac"].value == Decimal(0)
    assert metrics["vac"].favorability == "on_target"
    assert metrics["budget_pressure"].value == Decimal(-100)
    assert metrics["budget_pressure"].favorability == "favorable"
    assert metrics["period_actual_vs_planned"].availability == "period_required"


def test_cost_phasing_quarter_boundaries_are_calendar_quarters() -> None:
    key, starts_on, ends_on = SqlAlchemyFinancePerformanceReader._period_bounds(
        date(2026, 8, 15),
        "quarter",
    )

    assert key == "2026-Q3"
    assert starts_on == date(2026, 7, 1)
    assert ends_on == date(2026, 9, 30)


def test_cost_phasing_approved_baseline_calendar_allocation_is_exact(services, session) -> None:
    project = services["project_service"].create_project(
        "R6E baseline lifecycle", financial_currency_code="XAF"
    )
    approved_id = str(uuid4())
    for status in ("draft", "submitted", "rejected", "superseded", "approved"):
        baseline_id = approved_id if status == "approved" else str(uuid4())
        session.add(ProjectBaselineORM(
            id=baseline_id,
            project_id=project.id,
            name=status,
            created_at=date(2026, 12, 1),
            status=status,
            approved_at=date(2026, 12, 1) if status == "approved" else None,
        ))
        session.flush()
        session.add(BaselineTaskORM(
            id=str(uuid4()),
            baseline_id=baseline_id,
            task_id=str(uuid4()),
            baseline_start=date(2026, 12, 30),
            baseline_finish=date(2027, 1, 1),
            baseline_duration_days=3,
            baseline_planned_cost=Decimal("0.10") if status == "approved" else Decimal(100),
        ))
    session.flush()
    calendar = SimpleNamespace(working_day_dates_between=lambda _start, _end: (
        date(2026, 12, 30), date(2026, 12, 31), date(2027, 1, 1)
    ))
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test baseline phasing"
    )
    facts = SqlAlchemyFinancePerformanceReader(session=session, calendar=calendar).read_cost_phasing(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project.id,
        query=CostPhasingQuery(
            date_from=date(2026, 12, 30),
            date_to=date(2027, 1, 1),
            as_of_date=date(2026, 12, 31),
        ),
    )
    assert [row.period_key for row in facts.periods] == ["2026-12", "2027-01"]
    assert sum((row.planned_cost for row in facts.periods), Decimal(0)) == Decimal("0.10")
    assert all(row.planned_cost < Decimal(1) for row in facts.periods)
    assert facts.series_availability[0].availability == "available"


def test_sql_cost_phasing_reader_is_bounded_and_rejects_wrong_scope(
    services, session
) -> None:
    project = services["project_service"].create_project(
        "R6B Performance reader", financial_currency_code="XAF"
    )
    query = services["finance_performance_query"]

    with _statement_count(session) as statements:
        facts = query.get_cost_phasing(
            project.id,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
        )

    assert facts.project_id == project.id
    assert facts.currency_code == "XAF"
    # Project authority, Forecast authority, baseline inputs, and the three
    # monthly source aggregates are fixed-cost; source-row count cannot add SQL.
    assert len(statements) <= 8

    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test Performance scope"
    )
    assert (
        query._performance_reader.read_cost_phasing(
            tenant_id=scope.tenant_id,
            organization_id="wrong-organization",
            project_id=project.id,
            query=CostPhasingQuery(
                date_from=date(2026, 1, 1),
                date_to=date(2026, 12, 31),
            ),
        )
        is None
    )


def test_evm_reader_is_bounded_and_rejects_draft_baselines(services, session) -> None:
    project = services["project_service"].create_project(
        "R6E Decimal EVM reader", financial_currency_code="XAF"
    )
    services["task_service"].create_task(
        project.id, "Draft baseline task", start_date=date(2026, 1, 1), duration_days=2
    )
    services["baseline_service"].create_baseline(
        project.id, "Draft EVM baseline", rate_as_of=date(2026, 1, 1)
    )

    with _statement_count(session) as statements:
        result = services["reporting_service"].get_earned_value(
            project.id, as_of=date(2026, 1, 31)
        )

    assert result.availability == "baseline_unavailable"
    assert len(statements) <= 10


def test_variance_reader_is_bounded_without_per_task_queries(services, session) -> None:
    project = services["project_service"].create_project(
        "R6E Variance reader", financial_currency_code="XAF"
    )
    for number in range(8):
        services["task_service"].create_task(
            project.id,
            f"Variance task {number}",
            start_date=date(2026, 1, 1),
            duration_days=2,
        )
    services["baseline_service"].create_baseline(
        project.id, "Variance baseline", rate_as_of=date(2026, 1, 1)
    )

    with _statement_count(session) as statements:
        facts = services["finance_performance_query"].get_variance(
            project.id, as_of_date=date(2026, 1, 31)
        )

    assert facts.project_id == project.id
    # Includes bounded entitlement/context checks and one canonical EVM assembly.
    assert len(statements) <= 17


@pytest.mark.parametrize(
    "section_type",
    (
        "FinancialsEvmSection",
        "FinancialsVarianceSection",
        "FinancialsCostPhasingSection",
        "FinancialsReportsSection",
    ),
)
@pytest.mark.parametrize(
    ("width", "height"),
    ((1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)),
)
def test_performance_sections_load_at_supported_viewports(
    qapp,
    section_type: str,
    width: int,
    height: int,
) -> None:
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        f"""
import QtQuick
import workspaces.financials.cost_phasing.sections 1.0
import workspaces.financials.earned_value.sections 1.0
import workspaces.financials.reporting.sections 1.0
Window {{
    visible: true
    {section_type} {{
        objectName: "performanceSection"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
    }}
}}
""".encode(),
        QUrl(),
    )
    assert component.isReady(), [error.toString() for error in component.errors()]
    window = component.create()
    assert window is not None
    window.setProperty("width", width)
    window.setProperty("height", height)
    window.show()
    qapp.processEvents()
    section = window.findChild(QObject, "performanceSection")
    assert section is not None
    assert float(section.property("width")) >= width - 2
    assert float(section.property("implicitHeight")) > 0
    window.deleteLater()
