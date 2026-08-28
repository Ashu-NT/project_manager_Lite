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
from src.core.modules.project_management.contracts.reads.financials.models.finance_rate_facts import (
    RateCardRequest,
    RateLineRequest,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
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


def _seed_rates(services):
    project = services["project_service"].create_project(
        "R6B Rate Reader", financial_currency_code="USD"
    )
    rates = services["rate_card_service"]
    organization_card = rates.create_rate_card(name="Alpha Organization Rates")
    project_card = rates.create_rate_card(
        name="Zulu Project Rates", project_id=project.id
    )
    current = rates.create_line(
        project_card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("125.2500"),
        rate_currency="USD",
        role="engineer",
        effective_from=date(2026, 1, 1),
    )
    future = rates.create_line(
        project_card.id,
        rate_type=RateType.BILLING,
        unit="HOUR",
        rate_amount=Decimal("175.5000"),
        rate_currency="EUR",
        role="architect",
        effective_from=date(2027, 1, 1),
        effective_to=date(2027, 12, 31),
    )
    rates.create_line(
        organization_card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("80.0000"),
        rate_currency="USD",
        skill_code="python",
        effective_from=date(2025, 1, 1),
    )
    return project, organization_card, project_card, current, future


def test_rate_reader_is_bounded_sorted_filtered_and_selection_is_explicit(services):
    project, organization_card, project_card, _current, _future = _seed_rates(services)
    reader = services["finance_workspace_query"]._rate_reader
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test rate reader"
    )

    with _statement_count(services["session"]) as card_statements:
        cards = reader.list_cards(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project.id,
            request=RateCardRequest(page=1, page_size=1, sort_key="title"),
        )
    assert len(card_statements) == 2
    assert cards.total == 2
    assert cards.items[0].id == organization_card.id
    assert cards.items[0].line_count == 1

    project_cards = reader.list_cards(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project.id,
        request=RateCardRequest(scope="project", status="active", search="Zulu"),
    )
    assert project_cards.total == 1
    assert project_cards.items[0].id == project_card.id

    workspace = services["finance_workspace_query"].get_rate_workspace(project.id)
    assert workspace.selected_rate_card_id == ""
    assert workspace.selected_rate_card is None
    assert workspace.lines.items == ()


def test_selected_rate_card_detail_and_lines_are_bounded_and_effective_dated(services):
    project, _organization_card, project_card, current, future = _seed_rates(services)
    reader = services["finance_workspace_query"]._rate_reader
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test selected rates"
    )

    with _statement_count(services["session"]) as detail_statements:
        selected = reader.get_card(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project.id,
            rate_card_id=project_card.id,
        )
    with _statement_count(services["session"]) as line_statements:
        lines = reader.list_lines(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project.id,
            rate_card_id=project_card.id,
            request=RateLineRequest(
                page=1,
                page_size=1,
                sort_key="supportingText",
                sort_direction="asc",
                effective_status="current",
                as_of=date(2026, 8, 27),
            ),
        )
    assert len(detail_statements) == 1
    assert len(line_statements) == 2
    assert selected is not None and selected.line_count == 2
    assert lines.total == 1
    assert lines.items[0].id == current.id
    assert lines.items[0].rate_amount == Decimal("125.2500")
    assert lines.items[0].effective_status == "current"

    future_lines = reader.list_lines(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project.id,
        rate_card_id=project_card.id,
        request=RateLineRequest(
            rate_type="billing",
            effective_status="future",
            as_of=date(2026, 8, 27),
        ),
    )
    assert future_lines.total == 1
    assert future_lines.items[0].id == future.id


def test_rate_reader_denies_foreign_scope_and_desktop_keeps_decimal_strings(services):
    project, _organization_card, project_card, _current, _future = _seed_rates(services)
    query = services["finance_workspace_query"]
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test rate scope"
    )
    foreign = query._rate_reader.list_cards(
        tenant_id=scope.tenant_id,
        organization_id="foreign-organization",
        project_id=project.id,
        request=RateCardRequest(),
    )
    assert foreign.total == 0
    assert query._rate_reader.get_card(
        tenant_id=scope.tenant_id,
        organization_id="foreign-organization",
        project_id=project.id,
        rate_card_id=project_card.id,
    ) is None
    foreign_lines = query._rate_reader.list_lines(
        tenant_id=scope.tenant_id,
        organization_id="foreign-organization",
        project_id=project.id,
        rate_card_id=project_card.id,
        request=RateLineRequest(),
    )
    assert foreign_lines.total == 0

    dto = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=query
    ).get_rate_workspace(
        project.id,
        selected_rate_card_id=project_card.id,
        line_effective_status="current",
        as_of=date(2026, 8, 27),
    )
    assert dto.selected_rate_card_id == project_card.id
    assert Decimal(dto.lines[0].state["amount"]) == Decimal("125.2500")
    assert isinstance(dto.lines[0].state["amount"], str)
    assert dto.lines[0].state["currency"] == "USD"


def test_rate_destination_denies_finance_reader_without_sensitive_permission(services):
    project, *_ = _seed_rates(services)
    session = services["user_session"]
    session.set_principal(
        UserSessionPrincipal(
            user_id="limited-finance-reader",
            username="limited-finance-reader",
            display_name="Limited Finance Reader",
            role_names=frozenset({"project_manager"}),
            permissions=frozenset({"finance.read"}),
            active_tenant_id=session.stored_active_tenant_id(),
            active_organization_id=session.stored_active_organization_id(),
        )
    )
    with pytest.raises(BusinessRuleError, match="finance.read_sensitive") as exc:
        services["finance_workspace_query"].get_rate_workspace(project.id)
    assert exc.value.code == "PERMISSION_DENIED"


@pytest.mark.parametrize(
    ("width", "height"),
    ((1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)),
)
def test_rate_master_detail_loads_at_supported_viewports(qapp, width: int, height: int):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        b"""
import QtQuick
import workspaces.financials.sections 1.0
Window {
    visible: true
    FinancialsRateCardsSection {
        id: section
        objectName: "rateSection"
        anchors.fill: parent
        cards: ({"items": [{"id": "card-1"}], "page": 1, "pageSize": 50, "total": 1})
        selectedCardId: "card-1"
        selectedCard: ({"id": "card-1", "title": "Project Rates", "fields": []})
        lines: ({"items": [{"id": "line-1"}], "page": 1, "pageSize": 50, "total": 1})
    }
}
""",
        QUrl(),
    )
    assert component.isReady(), [error.toString() for error in component.errors()]
    root = component.create()
    assert root is not None
    root.setProperty("width", width)
    root.setProperty("height", height)
    root.show()
    qapp.processEvents()
    section = root.findChild(QObject, "rateSection")
    cards_table = root.findChild(QObject, "rateCardsTable")
    lines_table = root.findChild(QObject, "rateLinesTable")
    assert section is not None
    assert cards_table is not None and float(cards_table.property("width")) >= width - 2
    assert lines_table is not None and float(lines_table.property("width")) >= width - 2
    root.deleteLater()


def test_rate_qml_contract_is_server_read_only():
    source = (
        "src/ui_qml/modules/project_management/qml/workspaces/financials/sections/"
        "FinancialsRateCardsSection.qml"
    )
    text = open(source, encoding="utf-8").read()
    assert text.count('sortingMode: "server"') == 2
    assert "cardSelected" in text
    assert "lineFiltersRequested" in text
    assert "Add Rate" not in text
    assert "Create Rate" not in text
