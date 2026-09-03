from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlComponent

from src.core.modules.project_management.api.desktop.financials import (
    FinancialChangeCostCodeStatusCommand,
    FinancialCostCodeRestrictionCommand,
    FinancialCreateCostCodeCommand,
    FinancialTransitionProfileCommand,
    FinancialUpdateCostCodeCommand,
    FinancialUpdateProfileCommand,
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.application.financials.event_handlers.view_invalidation import (
    FINANCIAL_COST_CODE_CATALOG_SCOPE_CODE,
    FINANCIAL_COST_CODE_RESTRICTION_SCOPE_CODE,
    build_financial_profile_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.configuration_events import (
    CostCodeProfileUpdated,
    ProjectCostCodeRestrictionAdded,
)
from src.core.modules.project_management.domain.financials.configuration import CostCodePolicy
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError
from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.core.shared.events.domain_event_context import DomainEventContext
from src.ui_qml.modules.project_management.controllers.financials.financials_mutation_mixin import (
    FinancialsMutationMixin,
)
from src.ui_qml.shell.qml_engine import create_qml_engine


VIEWPORTS = ((1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080))
DIALOGS = (
    "CostCodeEditorDialog",
    "CostCodeRestrictionDialog",
    "FinancialProfileEditorDialog",
    "FinancialSetupLifecycleDialog",
)
DIALOG_ROOT = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/financials/dialogs"
).resolve()
SECTION_PATH = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/financials/sections/FinancialsProfileSection.qml"
).resolve()


def test_setup_reader_pages_filters_sorts_and_projects_capabilities(services) -> None:
    project = services["project_service"].create_project("R6C-E Setup")
    setup = services["financial_configuration_service"]
    profile = setup.get_profile(project.id)
    setup.configure_profile(
        project.id,
        expected_version=profile.version,
        cost_code_policy=CostCodePolicy.RESTRICTED,
    )
    alpha = setup.create_cost_code(
        code="R6CE.A", name="Alpha", available_to_project_id=project.id
    )
    setup.create_cost_code(code="R6CE.Z", name="Zulu")
    desktop = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"]
    )

    workspace = desktop.get_financial_setup_workspace(
        project.id,
        page_size=1,
        cost_code_sort_key="code",
        cost_code_sort_direction="desc",
    )
    assigned = desktop.get_financial_setup_workspace(
        project.id,
        cost_code_assignment="assigned",
        restriction_search="alpha",
    )

    assert workspace.cost_code_total == 2
    assert workspace.cost_codes[0].title == "R6CE.Z"
    assert assigned.cost_code_total == 1
    assert assigned.cost_codes[0].id == alpha.id
    assert assigned.restriction_total == 1
    assert assigned.can_create_cost_code is True
    assert assigned.can_manage_restrictions is True
    assert assigned.profile.state["canEdit"] is True


def test_setup_service_rejects_stale_edits_inactive_default_and_duplicate_restriction(
    services,
) -> None:
    project = services["project_service"].create_project("R6C-E Rules")
    setup = services["financial_configuration_service"]
    code = setup.create_cost_code(code="R6CE.RULE", name="Rules")
    inactive = setup.deactivate_cost_code(code.id, expected_version=code.version)
    profile = setup.get_profile(project.id)

    with pytest.raises(BusinessRuleError, match="active and effective"):
        setup.configure_profile(
            project.id,
            expected_version=profile.version,
            default_cost_code_id=inactive.id,
        )
    with pytest.raises(ConcurrencyError, match="changed since"):
        setup.update_cost_code(
            inactive.id,
            expected_version=code.version,
            name="Stale edit",
        )

    active = setup.activate_cost_code(inactive.id, expected_version=inactive.version)
    setup.add_project_cost_code(project_id=project.id, cost_code_id=active.id)
    with pytest.raises(BusinessRuleError, match="already assigned"):
        setup.add_project_cost_code(project_id=project.id, cost_code_id=active.id)


def test_setup_authorization_denies_hidden_project_and_missing_manage_permission(
    services,
) -> None:
    visible = services["project_service"].create_project("Visible Setup project")
    hidden = services["project_service"].create_project("Hidden Setup project")
    current = services["user_session"].principal
    assert current is not None
    tenant_id = services["user_session"].stored_active_tenant_id()
    organization_id = services["user_session"].stored_active_organization_id()
    api = ProjectManagementFinancialsDesktopApi(
        finance_workspace_query=services["finance_workspace_query"],
        finance_governance_commands=services["finance_governance_commands"],
    )

    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id=current.user_id,
            username=current.username,
            display_name=current.display_name,
            role_names=frozenset({"finance_test"}),
            permissions=frozenset({"finance.read", "finance.manage"}),
            scoped_access={
                "project": {
                    visible.id: frozenset({"finance.read", "finance.manage"})
                }
            },
            project_access={
                visible.id: frozenset({"finance.read", "finance.manage"})
            },
            active_tenant_id=tenant_id,
            active_organization_id=organization_id,
        )
    )
    with pytest.raises(BusinessRuleError, match="finance.read"):
        api.get_financial_setup_workspace(hidden.id)
    with pytest.raises(BusinessRuleError, match="finance.manage"):
        api.create_cost_code(
            FinancialCreateCostCodeCommand(
                project_id=hidden.id,
                code="HIDDEN",
                name="Hidden project code",
            )
        )

    services["user_session"].set_principal(
        UserSessionPrincipal(
            user_id=current.user_id,
            username=current.username,
            display_name=current.display_name,
            role_names=frozenset({"finance_reader"}),
            permissions=frozenset({"finance.read"}),
            scoped_access={"project": {visible.id: frozenset({"finance.read"})}},
            project_access={visible.id: frozenset({"finance.read"})},
            active_tenant_id=tenant_id,
            active_organization_id=organization_id,
        )
    )
    workspace = api.get_financial_setup_workspace(visible.id)
    assert workspace.can_create_cost_code is False
    with pytest.raises(BusinessRuleError, match="finance.manage"):
        api.create_cost_code(
            FinancialCreateCostCodeCommand(
                project_id=visible.id,
                code="READ-ONLY",
                name="Read-only code",
            )
        )


class _SetupBoundary:
    def __init__(self) -> None:
        self.service = SimpleNamespace()
        self.calls: list[tuple[str, tuple, dict]] = []
        for name in (
            "configure_profile",
            "transition_profile",
            "update_cost_code",
            "activate_cost_code",
            "deactivate_cost_code",
            "add_project_cost_code",
            "remove_project_cost_code",
        ):
            setattr(self.service, name, self._operation(name))

    def _operation(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return call

    def financial_setup(self, command, *, project_id=None):
        del project_id
        return command(self.service)


def test_typed_setup_commands_use_one_governance_boundary() -> None:
    boundary = _SetupBoundary()
    api = ProjectManagementFinancialsDesktopApi(
        finance_governance_commands=boundary  # type: ignore[arg-type]
    )
    api.update_financial_profile(
        FinancialUpdateProfileCommand(
            project_id="project-1",
            expected_version=3,
            currency_code="XAF",
            billing_method="non_billable",
            budget_control_mode="warn",
            cost_code_policy="all_active",
            financial_start_date=None,
            financial_end_date=None,
            is_funded=True,
            is_billable=False,
            default_cost_code_id=None,
        )
    )
    api.transition_financial_profile(
        FinancialTransitionProfileCommand("project-1", 4, "on_hold")
    )
    api.update_cost_code(
        FinancialUpdateCostCodeCommand(
            "code-1", 2, "LAB", "Labor", "", None, None, None, None, None
        )
    )
    api.change_cost_code_status(
        FinancialChangeCostCodeStatusCommand("code-1", 3, False)
    )
    command = FinancialCostCodeRestrictionCommand("project-1", "code-1")
    api.add_cost_code_restriction(command)
    api.remove_cost_code_restriction(command)

    assert [item[0] for item in boundary.calls] == [
        "configure_profile",
        "transition_profile",
        "update_cost_code",
        "deactivate_cost_code",
        "add_project_cost_code",
        "remove_project_cost_code",
    ]


def test_finance_mutation_rejects_duplicate_command_while_busy() -> None:
    class _BusyController(FinancialsMutationMixin):
        _is_busy = True

    operation_called = False

    def operation() -> None:
        nonlocal operation_called
        operation_called = True

    result = _BusyController()._run_finance_mutation(
        operation,
        "Should not complete.",
        on_success=lambda: None,
    )

    assert result == {
        "ok": False,
        "message": "A financial command is already in progress.",
        "code": "FINANCE_COMMAND_BUSY",
        "category": "busy",
    }
    assert operation_called is False


def test_setup_events_produce_targeted_catalog_and_restriction_hints() -> None:
    channel = SimpleNamespace(hints=[])
    channel.notify = channel.hints.append
    handler = build_financial_profile_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    context = DomainEventContext(correlation_id="r6ce-command")
    handler(
        CostCodeProfileUpdated(
            tenant_id="tenant-1",
            organization_id="org-1",
            cost_code_id="code-1",
            occurred_at=now,
        ),
        context,
    )
    handler(
        ProjectCostCodeRestrictionAdded(
            tenant_id="tenant-1",
            organization_id="org-1",
            project_id="project-1",
            cost_code_id="code-1",
            occurred_at=now,
        ),
        context,
    )

    assert [hint.scope_code for hint in channel.hints] == [
        FINANCIAL_COST_CODE_CATALOG_SCOPE_CODE,
        FINANCIAL_COST_CODE_RESTRICTION_SCOPE_CODE,
    ]
    assert channel.hints[0].entity_type == "organization"
    assert channel.hints[1].entity_id == "project-1"


@pytest.mark.parametrize(("width", "height"), VIEWPORTS)
@pytest.mark.parametrize("dialog_type", DIALOGS)
def test_setup_dialogs_fit_supported_viewports(
    qapp, dialog_type: str, width: int, height: int
) -> None:
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        dedent(
            f"""
            import QtQuick
            import QtQuick.Controls
            ApplicationWindow {{
                width: {width}; height: {height}; visible: true
                readonly property var setupDialog: loader.item
                Loader {{ id: loader; source: "{(DIALOG_ROOT / f'{dialog_type}.qml').as_uri()}"; onLoaded: item.open() }}
            }}
            """
        ).encode(),
        "r6ce-dialog.qml",
    )
    window = component.create()
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    dialog = window.property("setupDialog")
    assert dialog is not None
    assert 0 < float(dialog.property("width")) <= width
    assert 0 < float(dialog.property("height")) <= height
    assert dialog.findChild(QObject, "dialogSubmitButton") is not None
    assert dialog.findChild(QObject, "dialogCancelButton") is not None
    window.deleteLater()
    qapp.processEvents()


def test_setup_qml_uses_authoritative_tables_and_central_dialog_host() -> None:
    section = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/financials/sections/FinancialsProfileSection.qml"
    ).read_text(encoding="utf-8")
    host = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/financials/dialogs/FinancialsDialogHost.qml"
    ).read_text(encoding="utf-8")
    assert section.count('sortingMode:"server"') == 2
    assert "TablePaginationBar" in section
    assert "SearchablePagedSelector" in host or "CostCodeRestrictionDialog" in host
    for command in (
        "updateFinancialProfile",
        "updateCostCode",
        "changeCostCodeStatus",
        "addCostCodeRestriction",
        "removeCostCodeRestriction",
    ):
        assert f"workspaceController.{command}(" in host


@pytest.mark.parametrize(("width", "height"), VIEWPORTS)
def test_setup_section_loads_at_supported_viewports(qapp, width: int, height: int) -> None:
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        dedent(
            f"""
            import QtQuick
            import QtQuick.Controls
            ApplicationWindow {{
                width: {width}; height: {height}; visible: true
                Loader {{ anchors.fill: parent; source: "{SECTION_PATH.as_uri()}" }}
            }}
            """
        ).encode(),
        "r6ce-section.qml",
    )
    window = component.create()
    assert window is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    assert float(window.property("width")) == width
    window.deleteLater()
    qapp.processEvents()
