from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, QUrl, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent
from sqlalchemy import event

from src.core.modules.project_management.contracts.reads.resources import (
    ResourceCatalogReadItem,
    ResourceInspectorFact,
    ResourceSummaryFact,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.ui_qml.modules.project_management.controllers.resources.resource_read_handler import (
    load_resource_inspector,
)
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceInspectorViewModel,
)
from src.ui_qml.shell.qml_engine import create_qml_engine


def test_resource_read_facts_are_frozen_scalar_contracts() -> None:
    catalog = ResourceCatalogReadItem(
        resource_id="res-1",
        code="RES-001",
        name="Planner",
        role="Planner",
        worker_type="EMPLOYEE",
        cost_type="LABOR",
        is_active=True,
        capacity_percent=80.0,
        organization_id="org-1",
    )
    inspector = ResourceInspectorFact(
        resource_id="res-1",
        code="RES-001",
        name="Planner",
        role="Planner",
        worker_type="EMPLOYEE",
        is_active=True,
        capacity_percent=80.0,
        organization_id="org-1",
    )

    with pytest.raises(FrozenInstanceError):
        catalog.name = "Mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        inspector.project_count = 99  # type: ignore[misc]

    field_types = {
        str(field.type)
        for fact_type in (ResourceCatalogReadItem, ResourceInspectorFact, ResourceSummaryFact)
        for field in fields(fact_type)
    }
    assert not any("ResourceORM" in value for value in field_types)
    assert not any("domain.resources.resource.Resource" in value for value in field_types)


def test_resource_inspector_and_summary_are_scoped_bounded_independent_reads(services) -> None:
    resource_service = services["resource_service"]
    first = resource_service.create_resource(name="Alpha Planner", role="Planner")
    second = resource_service.create_resource(name="Zulu Planner", role="Planner")
    page = resource_service.query_catalog_page(page=1, page_size=1)
    assert [item.resource_id for item in page.items] == [first.id]

    session = services["project_service"]._session
    engine = session.get_bind()
    statements: list[str] = []

    def count_statement(_conn, _cursor, statement, _parameters, _context, _many) -> None:
        statements.append(str(statement))

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        inspector = resource_service.get_resource_inspector(second.id)
        inspector_statements = len(statements)
        statements.clear()
        summary = resource_service.get_resource_summary(second.id)
        summary_statements = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    assert inspector.resource_id == second.id
    assert inspector.can_read is True
    assert inspector.project_count == 0
    assert inspector.assignment_count == 0
    assert summary.resource_id == second.id
    assert summary.version == second.version
    assert inspector_statements <= 2
    assert summary_statements <= 2


def test_resource_inspector_and_summary_fail_closed_after_organization_switch(services) -> None:
    resource = services["resource_service"].create_resource(name="Scoped Planner")
    organization_service = services["organization_service"]
    original = organization_service.get_active_organization()
    other = organization_service.create_organization(
        organization_code="R5B-OTHER",
        display_name="R5B Other Organization",
        base_currency="EUR",
        is_active=False,
    )
    organization_service.set_active_organization(other.id)
    try:
        with pytest.raises(NotFoundError):
            services["resource_service"].get_resource_inspector(resource.id)
        with pytest.raises(NotFoundError):
            services["resource_service"].get_resource_summary(resource.id)
    finally:
        organization_service.set_active_organization(original.id)


def test_resource_inspector_and_summary_fail_closed_after_tenant_switch(services) -> None:
    resource = services["resource_service"].create_resource(name="Tenant Scoped Planner")
    resource_service = services["resource_service"]
    organization_id = services["user_session"].stored_active_organization_id()

    inspector = resource_service._resource_inspector_reader.read_inspector(
        tenant_id="r5b-other-tenant",
        organization_id=organization_id,
        resource_id=resource.id,
    )
    summary = resource_service._resource_summary_reader.read_summary(
        tenant_id="r5b-other-tenant",
        organization_id=organization_id,
        resource_id=resource.id,
    )

    assert inspector is None
    assert summary is None


def test_resource_inspector_and_summary_require_resource_read(services) -> None:
    resource = services["resource_service"].create_resource(name="Protected Planner")
    user_session = services["user_session"]
    original = user_session.principal
    assert original is not None
    user_session.set_principal(
        UserSessionPrincipal(
            user_id=original.user_id,
            username=original.username,
            display_name=original.display_name,
            role_names=frozenset(),
            permissions=frozenset({"organization.access"}),
            scoped_access=original.scoped_access,
            active_tenant_id=original.active_tenant_id,
            active_organization_id=original.active_organization_id,
        )
    )
    try:
        with pytest.raises(BusinessRuleError) as inspector_error:
            services["resource_service"].get_resource_inspector(resource.id)
        with pytest.raises(BusinessRuleError) as summary_error:
            services["resource_service"].get_resource_summary(resource.id)
        assert inspector_error.value.code == "PERMISSION_DENIED"
        assert summary_error.value.code == "PERMISSION_DENIED"
    finally:
        user_session.set_principal(original)


def test_inactive_resource_inspector_exposes_reactivate_only(services) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource(name="Inactive Planner")
    resource = resource_service.deactivate_resource(
        resource_id=resource.id,
        expected_version=resource.version,
    )

    inspector = resource_service.get_resource_inspector(resource.id)

    assert inspector.is_active is False
    assert inspector.can_deactivate is False
    assert inspector.can_reactivate is True


def test_resource_catalog_search_excludes_contact_and_address_pii(services) -> None:
    resource_service = services["resource_service"]
    resource_service.create_resource(
        name="Operational Planner",
        role="Scheduler",
        contact="private.search@example.com",
        address="Confidential Residence",
    )

    assert resource_service.query_catalog_page(search_text="Operational").filtered_total == 1
    assert resource_service.query_catalog_page(search_text="Scheduler").filtered_total == 1
    assert resource_service.query_catalog_page(search_text="private.search").filtered_total == 0
    assert resource_service.query_catalog_page(search_text="Confidential").filtered_total == 0


def test_stale_inspector_result_cannot_replace_newer_selection() -> None:
    controller = SimpleNamespace(
        _inspector_request_id=0,
        _selected_resource_id="res-b",
        _resource_inspector={"id": "res-b"},
        _inspector_loading=False,
        _inspector_error="",
    )

    class Presenter:
        def build_resource_inspector(self, _resource_id: str) -> ResourceInspectorViewModel:
            controller._inspector_request_id += 1
            return ResourceInspectorViewModel(id="res-a", title="Resource A")

    controller._resources_workspace_presenter = Presenter()
    controller._set_resource_inspector = lambda value: setattr(controller, "_resource_inspector", value)
    controller._set_inspector_loading = lambda value: setattr(controller, "_inspector_loading", value)
    controller._set_inspector_error = lambda value: setattr(controller, "_inspector_error", value)

    load_resource_inspector(controller, "res-a")

    assert controller._resource_inspector == {"id": "res-b"}


def test_r5b_resource_qml_uses_final_sections_and_actual_workspace_width() -> None:
    root = Path("src/ui_qml/modules/project_management/qml/workspaces/resources")
    page = (root / "ResourcesWorkspacePage.qml").read_text(encoding="utf-8")
    list_page = (root / "components/ResourcesListPage.qml").read_text(encoding="utf-8")
    state = (root / "ResourcesWorkspaceState.qml").read_text(encoding="utf-8")
    panel = (root / "panels/ResourcesDetailPanel.qml").read_text(encoding="utf-8")

    assert "root.width >= root._sideInspectorThreshold" in page
    assert "Theme.AppTheme.inspectorWidth + 720" in page
    assert "Window.width" not in page
    assert "InspectorPanel" in page
    assert "resourceInspectorModel" in page
    assert "Item {\n    id: root\n\n    property" in list_page
    assert "id: root\n\n    anchors.fill: parent" not in list_page
    assert '"Overview", "Capability", "Availability", "Projects", "Assignments", "Activity"' in state
    assert "ResourcesAvailabilitySection" in panel
    assert "No legacy capacity formula is shown here" not in panel
    assert "Assignment snapshots are not presented as history" in panel


@pytest.mark.parametrize(
    ("width", "height"),
    [(800, 640), (1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)],
)
def test_r5b_resource_workspace_runtime_geometry(qapp, width: int, height: int) -> None:
    messages: list[str] = []

    def capture_message(_message_type, _context, message: str) -> None:
        messages.append(str(message))

    previous_handler = qInstallMessageHandler(capture_message)
    try:
        engine = create_qml_engine()
        source = Path(
            "src/ui_qml/modules/project_management/qml/workspaces/resources/ResourcesWorkspacePage.qml"
        ).resolve()
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(source)))
        page = component.create()
        assert page is not None, "\n".join(error.toString() for error in component.errors())
        assert page.setProperty("width", width)
        assert page.setProperty("height", height)
        qapp.processEvents()

        catalog = page.findChild(QObject, "resourcesCatalogListPage")
        assert catalog is not None
        assert 0 < float(catalog.property("width")) <= width
        assert 0 < float(catalog.property("height")) <= height
        threshold = int(page.property("_sideInspectorThreshold"))
        assert bool(page.property("_useSideInspector")) is (width >= threshold)
    finally:
        qInstallMessageHandler(previous_handler)

    assert not any("managed by a layout" in message for message in messages), messages
    assert not any("is not a type" in message for message in messages), messages
