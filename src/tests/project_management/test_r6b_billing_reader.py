from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent
from sqlalchemy import event

from src.core.modules.project_management.api.desktop.financials import ProjectManagementFinancialsDesktopApi
from src.core.modules.project_management.contracts.reads.financials.models.finance_billing_facts import (
    AccountingStatusQuery,
    BillingPreparationLineQuery,
    BillingPreparationQuery,
    BillingScheduleQuery,
)
from src.core.modules.project_management.infrastructure.persistence.orm.billing import (
    ProjectBillingExternalEventORM,
    ProjectBillingPreparationLineORM,
    ProjectBillingPreparationORM,
    ProjectBillingProfileORM,
    ProjectBillingScheduleLineORM,
    ProjectBillingSourceLockORM,
)
from src.core.platform.infrastructure.persistence.orm.approval.approval import ApprovalRequestORM
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


def _seed_billing(services):
    project = services["project_service"].create_project(
        "R6B Billing Reader", financial_currency_code="USD"
    )
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="seed billing reader"
    )
    now = datetime(2026, 8, 28, 12, 0, tzinfo=timezone.utc)
    session = services["session"]
    session.add(ProjectBillingProfileORM(
        id="billing-profile-a", tenant_id=scope.tenant_id,
        organization_id=scope.organization_id, project_id=project.id,
        currency_code="USD", contract_reference="CONTRACT-2026",
        contract_value=Decimal("125000.2500"), customer_party_id="customer-a",
        external_customer_reference="ACCOUNT-77", purchase_order_reference="PO-99",
        cost_plus_markup_percent=Decimal("12.5000"), payment_terms_days=30,
        retention_years=7, legal_hold=False, status="active", version=2,
        created_by="admin", created_at=now, updated_by="admin", updated_at=now,
    ))
    session.flush()
    for identifier, name, due, status, amount in (
        ("schedule-alpha", "Alpha milestone", date(2026, 9, 1), "ready", Decimal("5000.2500")),
        ("schedule-zulu", "Zulu milestone", date(2026, 10, 1), "planned", Decimal("7000.5000")),
    ):
        session.add(ProjectBillingScheduleLineORM(
            id=identifier, tenant_id=scope.tenant_id,
            organization_id=scope.organization_id, project_id=project.id,
            billing_profile_id="billing-profile-a", name=name, amount=amount,
            currency_code="USD", due_date=due, task_id=None,
            acceptance_reference=f"ACCEPT-{identifier}", status=status, version=1,
            created_by="admin", created_at=now, updated_by="admin", updated_at=now,
        ))
    session.add(ApprovalRequestORM(
        id="billing-approval-a", tenant_id=scope.tenant_id,
        request_type="billing.approve", entity_type="billing_preparation",
        entity_id="preparation-alpha", organization_id=scope.organization_id,
        project_id=project.id, payload_json="{}", status="APPROVED",
        requested_by_username="commercial.manager", requested_at=now,
        decided_by_username="finance.approver", decided_at=now,
        decision_note="Commercial package approved.",
    ))
    session.flush()
    for identifier, number, status, created_at in (
        ("preparation-alpha", "BP-0001", "delivery_pending", now),
        ("preparation-zulu", "BP-0002", "delivery_pending", now.replace(hour=13)),
    ):
        session.add(ProjectBillingPreparationORM(
            id=identifier, tenant_id=scope.tenant_id,
            organization_id=scope.organization_id, project_id=project.id,
            billing_profile_id="billing-profile-a", preparation_number=number,
            billing_method="fixed_price", period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31), currency_code="USD",
            idempotency_key=f"key-{identifier}", status=status,
            line_count=1 if identifier == "preparation-alpha" else 0,
            total_amount=Decimal("5000.2500") if identifier == "preparation-alpha" else Decimal("0"),
            correction_of_preparation_id=None,
            approval_request_id="billing-approval-a" if identifier == "preparation-alpha" else None,
            submitted_by="commercial.manager" if identifier == "preparation-alpha" else None,
            submitted_at=now if identifier == "preparation-alpha" else None,
            approved_by="finance.approver" if identifier == "preparation-alpha" else None,
            approved_at=now if identifier == "preparation-alpha" else None,
            rejected_by=None, rejected_at=None, rejection_notes="",
            delivery_requested_at=now,
            delivered_at=None, acknowledged_at=None, reconciled_at=None,
            version=2 if identifier == "preparation-alpha" else 1,
            created_by="commercial.manager", created_at=created_at, updated_at=created_at,
        ))
    session.flush()
    session.add(ProjectBillingPreparationLineORM(
        id="preparation-line-a", tenant_id=scope.tenant_id,
        organization_id=scope.organization_id, project_id=project.id,
        preparation_id="preparation-alpha", source_type="schedule_line",
        source_id="schedule-alpha", source_revision="1", source_content_hash="a" * 64,
        description="Accepted milestone", source_date=date(2026, 9, 1),
        quantity=Decimal("1"), unit="milestone", unit_rate=Decimal("5000.2500"),
        net_amount=Decimal("5000.2500"), currency_code="USD", task_id=None,
        resource_id=None, source_amount=Decimal("5000.2500"), markup_percent=None,
        rate_card_id=None, rate_line_id=None, rate_card_version=None, created_at=now,
    ))
    session.add(ProjectBillingSourceLockORM(
        id="source-lock-a", tenant_id=scope.tenant_id,
        organization_id=scope.organization_id, project_id=project.id,
        source_type="schedule_line", source_id="schedule-alpha", source_revision="1",
        source_content_hash="a" * 64, preparation_id="preparation-alpha",
        preparation_line_id="preparation-line-a", status="finalized",
        reserved_at=now, finalized_at=now, released_at=None,
    ))
    session.add(ProjectBillingExternalEventORM(
        id="external-event-a", tenant_id=scope.tenant_id,
        organization_id=scope.organization_id, project_id=project.id,
        preparation_id="preparation-alpha", event_type="delivery_accepted",
        external_system="ACCOUNTING", external_status="accepted",
        idempotency_key="external-a", occurred_at=now,
        external_invoice_reference="INV-EXT-7", reconciliation_reference=None,
        message="Accepted by Accounting integration.", recorded_at=now,
    ))
    session.commit()
    return project, scope


def test_billing_readers_are_bounded_sorted_filtered_and_selection_is_explicit(services):
    project, scope = _seed_billing(services)
    reader = services["finance_workspace_query"]._billing_reader
    with _statement_count(services["session"]) as schedule_statements:
        schedule = reader.list_schedule(
            tenant_id=scope.tenant_id, organization_id=scope.organization_id,
            project_id=project.id,
            request=BillingScheduleQuery(page_size=1, sort_key="title", sort_direction="asc"),
        )
    with _statement_count(services["session"]) as preparation_statements:
        preparations = reader.list_preparations(
            tenant_id=scope.tenant_id, organization_id=scope.organization_id,
            project_id=project.id,
            request=BillingPreparationQuery(page_size=1, sort_key="title", sort_direction="asc"),
        )
    assert len(schedule_statements) == 2
    assert len(preparation_statements) == 2
    assert schedule.total == 2 and schedule.items[0].id == "schedule-alpha"
    assert schedule.items[0].source_state == "finalized"
    assert preparations.total == 2 and preparations.items[0].id == "preparation-alpha"
    assert preparations.items[0].latest_external_status == "accepted"
    assert reader.list_schedule(
        tenant_id=scope.tenant_id, organization_id=scope.organization_id,
        project_id=project.id,
        request=BillingScheduleQuery(page_size=1, sort_key="title", sort_direction="desc"),
    ).items[0].id == "schedule-zulu"
    assert reader.list_preparations(
        tenant_id=scope.tenant_id, organization_id=scope.organization_id,
        project_id=project.id,
        request=BillingPreparationQuery(page_size=1, sort_key="title", sort_direction="desc"),
    ).items[0].id == "preparation-zulu"
    assert reader.list_schedule(
        tenant_id=scope.tenant_id, organization_id=scope.organization_id,
        project_id=project.id, request=BillingScheduleQuery(status="ready", source_state="finalized"),
    ).total == 1
    workspace = services["finance_workspace_query"].get_billing_read_workspace(project.id)
    assert workspace.selected_preparation_id == ""
    assert workspace.selected_preparation is None
    assert workspace.lines.items == ()


def test_accounting_status_reader_is_bounded_isolated_and_scope_safe(services):
    project, scope = _seed_billing(services)
    reader = services["finance_workspace_query"]._billing_reader

    with _statement_count(services["session"]) as statements:
        page = reader.list_accounting_statuses(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project.id,
            request=AccountingStatusQuery(page_size=1, search="ACCOUNTING"),
        )

    assert len(statements) == 2
    normalized_sql = " ".join(statements).lower()
    assert "project_billing_profiles" not in normalized_sql
    assert "project_billing_schedule_lines" not in normalized_sql
    assert "project_billing_preparation_lines" not in normalized_sql
    assert page.total == 1
    assert page.items[0].preparation_number == "BP-0001"
    assert page.items[0].latest_external_status == "accepted"
    assert page.items[0].latest_external_invoice_reference == "INV-EXT-7"
    assert reader.list_accounting_statuses(
        tenant_id="foreign-tenant",
        organization_id=scope.organization_id,
        project_id=project.id,
        request=AccountingStatusQuery(),
    ).total == 0
    assert reader.list_accounting_statuses(
        tenant_id=scope.tenant_id,
        organization_id="foreign-organization",
        project_id=project.id,
        request=AccountingStatusQuery(),
    ).total == 0


def test_selected_billing_detail_and_lines_are_bounded_and_truthful(services):
    project, scope = _seed_billing(services)
    reader = services["finance_workspace_query"]._billing_reader
    with _statement_count(services["session"]) as detail_statements:
        detail = reader.get_preparation(
            tenant_id=scope.tenant_id, organization_id=scope.organization_id,
            project_id=project.id, preparation_id="preparation-alpha",
        )
    with _statement_count(services["session"]) as line_statements:
        lines = reader.list_preparation_lines(
            tenant_id=scope.tenant_id, organization_id=scope.organization_id,
            project_id=project.id, preparation_id="preparation-alpha",
            request=BillingPreparationLineQuery(page_size=1, source_type="schedule_line"),
        )
    assert len(detail_statements) == 1
    assert len(line_statements) == 2
    assert detail is not None
    assert detail.approval_status == "APPROVED"
    assert detail.lock_count == 1 and detail.finalized_lock_count == 1
    assert detail.latest_external_invoice_reference == "INV-EXT-7"
    assert lines.total == 1
    assert lines.items[0].net_amount == Decimal("5000.2500")
    assert lines.items[0].source_state == "finalized"

    dto = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"]
    ).get_billing_read_workspace(project.id, selected_preparation_id="preparation-alpha")
    assert dto.selected_preparation_id == "preparation-alpha"
    delivery = next(field for field in dto.selected_preparation.fields if field[0] == "Delivery evidence")
    assert delivery[1] == "External Accounting outcome received"
    assert isinstance(dto.lines[0].state["netAmount"], str)
    assert Decimal(dto.lines[0].state["netAmount"]) == Decimal("5000.2500")

    local_only = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"]
    ).get_billing_read_workspace(project.id, selected_preparation_id="preparation-zulu")
    local_delivery = next(field for field in local_only.selected_preparation.fields if field[0] == "Delivery evidence")
    assert local_delivery[1] == "Local handoff requested"
    assert "No durable Accounting" in local_delivery[2]


def test_billing_reader_denies_wrong_project_parent_scope(services):
    project, scope = _seed_billing(services)
    other = services["project_service"].create_project("Other Billing Project", financial_currency_code="USD")
    reader = services["finance_workspace_query"]._billing_reader
    assert reader.get_preparation(
        tenant_id=scope.tenant_id, organization_id=scope.organization_id,
        project_id=other.id, preparation_id="preparation-alpha",
    ) is None
    assert reader.list_preparation_lines(
        tenant_id=scope.tenant_id, organization_id=scope.organization_id,
        project_id=other.id, preparation_id="preparation-alpha",
        request=BillingPreparationLineQuery(),
    ).total == 0
    assert project.id != other.id


def test_billing_workspace_requires_finance_read_permission(services):
    project, _scope = _seed_billing(services)
    session = services["user_session"]
    session.set_principal(UserSessionPrincipal(
        user_id="billing-reader-without-finance",
        username="billing-reader-without-finance",
        display_name="No Billing Reader",
        role_names=frozenset(), permissions=frozenset(),
        active_tenant_id=session.stored_active_tenant_id(),
        active_organization_id=session.stored_active_organization_id(),
    ))
    with pytest.raises(BusinessRuleError) as exc:
        services["finance_workspace_query"].get_billing_read_workspace(project.id)
    assert exc.value.code == "PERMISSION_DENIED"


@pytest.mark.parametrize(
    ("width", "height"),
    ((1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)),
)
def test_billing_master_detail_loads_at_supported_viewports(qapp, width: int, height: int):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        b'''
import QtQuick
import workspaces.financials.sections 1.0
Window {
    visible: true
    FinancialsBillingPreparationSection {
        id: section
        objectName: "billingSection"
        anchors.fill: parent
        profile: ({"title": "Billing Profile", "fields": []})
        schedule: ({"items": [{"id": "schedule-1"}], "page": 1, "pageSize": 50, "total": 1})
        preparations: ({"items": [{"id": "preparation-1"}], "page": 1, "pageSize": 50, "total": 1})
        selectedPreparationId: "preparation-1"
        selectedPreparation: ({"id": "preparation-1", "title": "BP-0001", "fields": []})
        lines: ({"items": [{"id": "line-1"}], "page": 1, "pageSize": 50, "total": 1})
    }
}
''',
        QUrl(),
    )
    assert component.isReady(), [error.toString() for error in component.errors()]
    window = component.create()
    assert window is not None
    window.setProperty("width", width)
    window.setProperty("height", height)
    window.show()
    qapp.processEvents()
    assert window.findChild(QObject, "billingScheduleTable") is not None
    assert window.findChild(QObject, "billingPreparationsTable") is not None
    assert window.findChild(QObject, "billingPreparationLinesTable") is not None
    window.deleteLater()


def test_billing_qml_contract_is_server_read_only():
    source = "src/ui_qml/modules/project_management/qml/workspaces/financials/sections/FinancialsBillingPreparationSection.qml"
    text = open(source, encoding="utf-8").read()
    assert text.count('sortingMode: "server"') == 3
    assert "preparationSelected" in text
    assert "Local handoff" not in text
    for forbidden in ('text: "Create Preparation"', 'text: "Approve Preparation"', 'text: "Deliver"', 'text: "Edit Profile"'):
        assert forbidden not in text


def test_billing_filter_helpers_are_safe_during_qml_initialization():
    source = "src/ui_qml/modules/project_management/qml/workspaces/financials/sections/FinancialsBillingPreparationSection.qml"
    text = open(source, encoding="utf-8").read()
    assert "replaceAll" not in text
    assert "if (!model || model.length === undefined) return 0" in text
