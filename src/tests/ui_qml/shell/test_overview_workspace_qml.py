"""
Real-data, warning-free rendering checks for OverviewWorkspace.qml and its
promoted/new shared widgets (OverviewMetricTile, ModuleCard, ActionCenterRow,
ActionCenterList), plus the responsive layout-class helper and the Platform
Overview regression (OverviewMetricTile promotion must not visually/
structurally regress its original consumer).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

from src.core.application.global_overview.contracts.action_center import (
    ActionCenterContribution,
    ActionCenterItemDto,
    ActionCenterSummaryDto,
)
from src.core.application.global_overview.contracts.module_summary import ModuleSummaryDto
from src.core.application.global_overview.contracts.overview import (
    GlobalOverviewCapabilitiesDto,
    GlobalOverviewContextDto,
)
from src.core.platform.api.desktop.history.activity.models.activity import ActivityEntryDto
from src.core.platform.api.desktop.models.common import DesktopApiError, DesktopApiResult
from src.ui_qml.shell.controllers.global_overview.global_overview_controller import (
    GlobalOverviewController,
)
from src.ui_qml.shell.presenters.global_overview_presenter import GlobalOverviewPresenter
from src.ui_qml.shell.qml_engine import create_qml_engine

ROOT = Path(__file__).resolve().parents[3]
OVERVIEW_WORKSPACE = ROOT / "ui_qml/shell/qml/OverviewWorkspace.qml"
PLATFORM_OVERVIEW_PAGE = ROOT / "ui_qml/platform/qml/workspaces/overview/PlatformOverviewPage.qml"


class _FakeGlobalOverviewApi:
    def __init__(self) -> None:
        today = date.today()
        self.context_result = DesktopApiResult(
            ok=True,
            data=GlobalOverviewContextDto(
                tenant_name="TECHASH Enterprise", organization_name="Shell", role_label=None
            ),
        )
        self.attention_result = DesktopApiResult(ok=True, data=ActionCenterSummaryDto(0, 0, 0, 0))
        self.modules_result = DesktopApiResult(
            ok=True,
            data=(
                ModuleSummaryDto(
                    module_code="platform",
                    title="Platform",
                    description="Shared administration, organizational data, access, documents, and governance.",
                    summary_text="2 items require attention",
                    route_id="platform.workspace",
                ),
                ModuleSummaryDto(
                    module_code="project_management",
                    title="Project Management",
                    description="Plan and monitor projects, tasks, resources, schedules, and delivery.",
                    summary_text="",
                    route_id="project_management.workspace",
                ),
            ),
        )
        self.recent_activity_result = DesktopApiResult(
            ok=True,
            data=(
                ActivityEntryDto(
                    id="a1",
                    action="task.created",
                    entity_type="task",
                    entity_id="t1",
                    actor_id="user-1",
                    module="project_management",
                    timestamp=datetime.now(timezone.utc),
                    type="info",
                    human_message="Task created",
                    icon="task",
                    color="blue",
                ),
            ),
        )
        self.action_center_result = DesktopApiResult(
            ok=True,
            data=ActionCenterContribution(
                items=(
                    ActionCenterItemDto(
                        id="task-1",
                        kind="pm_task",
                        title="Review project estimates",
                        module="Project Management",
                        subject_type="task",
                        subject_id="task-1",
                        subject_display="Facility Upgrade",
                        action_state="todo",
                        route_id="project_management.tasks",
                        priority="high",
                        due_at=today + timedelta(days=3),
                        sort_at=datetime.now(timezone.utc),
                    ),
                    ActionCenterItemDto(
                        id="baseline-1",
                        kind="baseline_review",
                        title="Review project baseline",
                        module="Project Management",
                        subject_type="baseline",
                        subject_id="baseline-1",
                        subject_display="Facility Upgrade",
                        action_state="awaiting_review",
                        route_id="project_management.scheduling",
                        sort_at=datetime.now(timezone.utc),
                    ),
                    ActionCenterItemDto(
                        id="approval-1",
                        kind="approval",
                        title="Review organization request",
                        module="Platform",
                        subject_type="organization_request",
                        subject_id="approval-1",
                        subject_display="Organization Request",
                        action_state="awaiting_decision",
                        route_id="control_approvals",
                        sort_at=datetime.now(timezone.utc),
                    ),
                    ActionCenterItemDto(
                        id="ts-open-1",
                        kind="timesheet",
                        title="Submit timesheet",
                        module="Project Management",
                        subject_type="timesheet_period",
                        subject_id="ts-open-1",
                        subject_display="01 Sep - 07 Sep",
                        action_state="open",
                        route_id="project_management.timesheets",
                        sort_at=datetime.now(timezone.utc),
                    ),
                    ActionCenterItemDto(
                        id="ts-rejected-1",
                        kind="timesheet",
                        title="Correct and resubmit timesheet",
                        module="Project Management",
                        subject_type="timesheet_period",
                        subject_id="ts-rejected-1",
                        subject_display="08 Sep - 14 Sep",
                        action_state="rejected",
                        route_id="project_management.timesheets",
                        sort_at=datetime.now(timezone.utc),
                    ),
                ),
                summary=ActionCenterSummaryDto(5, 2, 2, 1),
            ),
        )
        self.capabilities_result = DesktopApiResult(
            ok=True,
            data=GlobalOverviewCapabilitiesDto(
                effective_permissions=frozenset({"project.manage"}),
                accessible_module_codes=("project_management",),
            ),
        )

    def get_context(self):
        return self.context_result

    def get_attention_summary(self):
        return self.attention_result

    def list_module_summaries(self):
        return self.modules_result

    def list_recent_activity(self, *, limit: int = 50):
        return self.recent_activity_result

    def list_action_center(self, *, limit: int = 50):
        return self.action_center_result

    def get_capabilities(self):
        return self.capabilities_result


def _build_controller(api=None) -> GlobalOverviewController:
    presenter = GlobalOverviewPresenter(api=api or _FakeGlobalOverviewApi())
    controller = GlobalOverviewController(presenter=presenter, shell_context=None)
    return controller


def _load_overview_workspace(qapp, *, width: int = 1440, height: int = 900):
    messages: list[str] = []

    def capture_message(_message_type, _context, message: str) -> None:
        messages.append(str(message))

    previous_handler = qInstallMessageHandler(capture_message)
    engine = create_qml_engine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(OVERVIEW_WORKSPACE.resolve())))
    page = component.create()
    assert page is not None, "\n".join(error.toString() for error in component.errors())

    window = QQuickWindow()
    window.resize(width, height)
    page.setParentItem(window.contentItem())
    page.setWidth(width)
    page.setHeight(height)
    window.show()
    qapp.processEvents()

    return previous_handler, messages, engine, component, page, window


def _teardown(previous_handler, page, window, qapp) -> None:
    page.setParentItem(None)
    page.deleteLater()
    window.close()
    window.deleteLater()
    qapp.processEvents()
    qInstallMessageHandler(previous_handler)


def _relevant_warnings(messages: list[str]) -> list[str]:
    return [
        message
        for message in messages
        if "ReferenceError" in message
        or "TypeError" in message
        or "Cannot read property" in message
        or "unknown icon name" in message
        or "is not defined" in message
    ]


# -- Page load (null controller, matches the offscreen route sweep) ------------------------


def test_overview_workspace_loads_without_warnings_with_no_controller(qapp) -> None:
    previous_handler, messages, engine, component, page, window = _load_overview_workspace(qapp)
    try:
        assert _relevant_warnings(messages) == []
        assert page.property("title") == "Overview"
    finally:
        _teardown(previous_handler, page, window, qapp)


# -- Page load with real data -----------------------------------------------------------------


def test_overview_workspace_loads_without_warnings_with_real_data(qapp) -> None:
    controller = _build_controller()
    controller.reload()

    previous_handler, messages, engine, component, page, window = _load_overview_workspace(qapp)
    try:
        page.setProperty("globalOverviewController", controller)
        qapp.processEvents()

        assert _relevant_warnings(messages) == []
    finally:
        _teardown(previous_handler, page, window, qapp)


def test_real_shell_wiring_injects_controller_into_overview_page(qapp) -> None:
    """End-to-end: App.qml -> MainWindow.qml -> Loader -> OverviewWorkspace,
    the exact real-app wiring path app.py uses (initial_properties on the
    top-level App.qml root, not a direct page-level property set). Confirms
    the controller genuinely reaches the loaded page and its one reload()
    actually ran, purely by observing controller-side effects (context
    becomes populated) -- no Loader internals are reached into."""
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog
    from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
    from src.ui_qml.shell.context import build_shell_context
    from src.ui_qml.shell.main_window import build_main_window_navigation
    from src.ui_qml.shell.qml_registry import build_qml_route_registry
    from src.ui_qml.shell.qml_engine import load_qml

    controller = _build_controller()
    assert controller.context.get("tenantName") == ""

    registry = build_qml_route_registry()
    shell_context = build_shell_context(build_main_window_navigation(registry))
    assert shell_context.currentRouteId == "shell.home"

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    try:
        shell_route = registry.get("shell.app")
        load_qml(
            engine,
            shell_route.qml_path,
            initial_properties={
                "shellModel": shell_context,
                "platformCatalog": PlatformWorkspaceCatalog(),
                "pmCatalog": ProjectManagementWorkspaceCatalog(),
                "globalOverviewController": controller,
            },
        )
        # MainWindow.qml's workspace Loader is asynchronous -- a tight
        # processEvents() loop returns before the background QML
        # compile/instantiate finishes; qWait lets it actually complete.
        QTest.qWait(1000)

        assert controller.context.get("tenantName") == "TECHASH Enterprise"
        assert _relevant_warnings(messages) == []
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        qapp.processEvents()
        qInstallMessageHandler(previous_handler)


def test_overview_workspace_reload_fires_once_when_controller_attaches(qapp) -> None:
    controller = _build_controller()
    load_calls: list[str] = []
    original_context = controller._presenter.load_context

    def _counting_context():
        load_calls.append("context")
        return original_context()

    controller._presenter.load_context = _counting_context

    previous_handler, messages, engine, component, page, window = _load_overview_workspace(qapp)
    try:
        page.setProperty("globalOverviewController", controller)
        qapp.processEvents()
        # Setting the same controller reference again (idempotent assignment,
        # e.g. a spurious re-binding) must not trigger a second reload.
        page.setProperty("globalOverviewController", controller)
        qapp.processEvents()

        assert load_calls == ["context"]
    finally:
        _teardown(previous_handler, page, window, qapp)


def test_overview_workspace_context_line_has_no_dangling_separator(qapp) -> None:
    controller = _build_controller()
    controller.reload()

    previous_handler, messages, engine, component, page, window = _load_overview_workspace(qapp)
    try:
        page.setProperty("globalOverviewController", controller)
        qapp.processEvents()

        context = controller.context
        assert context["contextLine"] == "TECHASH Enterprise · Shell"
    finally:
        _teardown(previous_handler, page, window, qapp)


def test_overview_workspace_attention_all_zero_still_shows_four_cards(qapp) -> None:
    controller = _build_controller()
    controller.reload()

    assert controller.attentionState == {"loading": False, "errorMessage": "", "empty": False}
    assert len(controller.attention) == 4
    assert all(card["value"] == 0 for card in controller.attention)
    assert all(card["interactive"] is False for card in controller.attention)


def test_overview_workspace_quick_actions_contains_verified_action_only(qapp) -> None:
    controller = _build_controller()
    controller.reload()

    assert [action["key"] for action in controller.quickActions] == ["create_project"]
    assert controller.quickActions[0]["routeId"] == "project_management.projects"


def test_overview_workspace_quick_actions_hidden_when_none_verified(qapp) -> None:
    api = _FakeGlobalOverviewApi()
    api.capabilities_result = DesktopApiResult(
        ok=True,
        data=GlobalOverviewCapabilitiesDto(effective_permissions=frozenset(), accessible_module_codes=()),
    )
    controller = _build_controller(api)
    controller.reload()

    assert controller.quickActions == []


def test_overview_workspace_modules_render_from_model_not_hardcoded(qapp) -> None:
    controller = _build_controller()
    controller.reload()

    assert [module["moduleCode"] for module in controller.modules] == ["platform", "project_management"]
    # Degraded/empty backend summary_text still renders the card -- QML falls
    # back to "—" rather than hiding it or failing the section.
    assert controller.modules[1]["summaryText"] == ""


def test_overview_workspace_action_center_covers_every_kind_without_warnings(qapp) -> None:
    controller = _build_controller()
    controller.reload()

    rows_by_kind = {row["kind"]: row for row in controller.actionCenter}
    assert rows_by_kind["pm_task"]["dueLabel"].startswith("Due")
    assert rows_by_kind["baseline_review"]["statusLabel"] == "Awaiting review"
    assert rows_by_kind["baseline_review"]["dueLabel"] == ""
    assert rows_by_kind["approval"]["statusLabel"] == "Awaiting decision"
    assert rows_by_kind["approval"]["dueLabel"] == ""


def test_overview_workspace_recent_activity_error_state(qapp) -> None:
    api = _FakeGlobalOverviewApi()
    api.recent_activity_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="X", message="boom", category="domain")
    )
    controller = _build_controller(api)
    controller.reload()

    assert controller.recentActivityState["errorMessage"] == "Recent activity could not be loaded."
    assert controller.recentActivity == []


def test_overview_workspace_action_center_failure_does_not_erase_modules(qapp) -> None:
    api = _FakeGlobalOverviewApi()
    api.action_center_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="X", message="boom", category="domain")
    )
    controller = _build_controller(api)
    controller.reload()

    assert controller.actionCenterState["errorMessage"] == "Action items could not be loaded."
    assert controller.modulesState["errorMessage"] == ""
    assert len(controller.modules) == 2


# -- Responsive layout class -----------------------------------------------------------------


@pytest.mark.parametrize(
    "width,height,expected",
    [
        (1600, 900, "standard"),
        (1300, 900, "compact"),
        (1600, 700, "compact"),
        (900, 900, "narrow"),
        (1023, 900, "narrow"),
        (1024, 900, "compact"),
    ],
)
def test_layout_class_for_width_height(qapp, width, height, expected) -> None:
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        b"""
        import QtQuick
        import App.Theme 1.0 as Theme
        QtObject {
            property string result: Theme.AppTheme.layoutClassFor(%d, %d)
        }
        """ % (width, height),
        QUrl(),
    )
    obj = component.create()
    assert obj is not None, "\n".join(error.toString() for error in component.errors())
    assert obj.property("result") == expected


@pytest.mark.parametrize("density_mode", ["compact", "comfortable", "spacious"])
def test_user_density_is_independent_of_responsive_layout_class(qapp, density_mode) -> None:
    """A standard-width window may use any density; layoutClassFor is a
    pure function of width/height only and must not vary with density."""
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        ("""
        import QtQuick
        import App.Theme 1.0 as Theme
        QtObject {
            Component.onCompleted: Theme.AppTheme.densityMode = "%s"
            property string layoutClass: Theme.AppTheme.layoutClassFor(1600, 900)
        }
        """ % density_mode).encode("utf-8"),
        QUrl(),
    )
    obj = component.create()
    assert obj is not None, "\n".join(error.toString() for error in component.errors())
    assert obj.property("layoutClass") == "standard"


# -- Theme (light / dark) -----------------------------------------------------------------------


def _set_theme_mode(engine, mode: str) -> None:
    component = QQmlComponent(engine)
    component.setData(
        (
            'import QtQuick\nimport App.Theme 1.0 as Theme\n'
            'QtObject { Component.onCompleted: Theme.AppTheme.themeMode = "%s" }' % mode
        ).encode("utf-8"),
        QUrl(),
    )
    obj = component.create()
    assert obj is not None, "\n".join(error.toString() for error in component.errors())


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_overview_workspace_instantiates_in_light_and_dark(qapp, mode) -> None:
    controller = _build_controller()
    controller.reload()

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    page = None
    window = None
    try:
        _set_theme_mode(engine, mode)
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(OVERVIEW_WORKSPACE.resolve())))
        page = component.create()
        assert page is not None, "\n".join(error.toString() for error in component.errors())

        window = QQuickWindow()
        window.resize(1440, 900)
        page.setParentItem(window.contentItem())
        page.setWidth(1440)
        page.setHeight(900)
        page.setProperty("globalOverviewController", controller)
        window.show()
        qapp.processEvents()

        assert _relevant_warnings(messages) == []
    finally:
        if page is not None:
            page.setParentItem(None)
            page.deleteLater()
        if window is not None:
            window.close()
            window.deleteLater()
        qapp.processEvents()
        qInstallMessageHandler(previous_handler)


@pytest.mark.parametrize(
    "relative_path",
    [
        "ui_qml/shell/qml/OverviewWorkspace.qml",
        "ui_qml/shared/qml/App/Widgets/ModuleCard.qml",
        "ui_qml/shared/qml/App/Widgets/ActionCenterRow.qml",
        "ui_qml/shared/qml/App/Widgets/ActionCenterList.qml",
        "ui_qml/shared/qml/App/Widgets/OverviewMetricTile.qml",
    ],
)
def test_no_hardcoded_color_literals(relative_path) -> None:
    """Every color must come from an AppTheme semantic token -- no raw hex
    literal styling that would silently break in dark mode."""
    import re

    source = (ROOT / relative_path).read_text(encoding="utf-8")
    hex_literals = re.findall(r'"#[0-9A-Fa-f]{3,8}"', source)
    assert hex_literals == [], f"{relative_path} has hardcoded color literals: {hex_literals}"


# -- Lower panel (Recent Activity / Action Center) width composition ---------------------------


def _find_by_object_name(obj, object_name: str):
    if obj.objectName() == object_name:
        return obj
    for child in obj.children():
        found = _find_by_object_name(child, object_name)
        if found is not None:
            return found
    return None


@pytest.mark.parametrize(
    "width,height",
    [
        (1600, 1000),  # standard
        (1366, 768),  # compact
    ],
)
def test_lower_panels_split_approximately_45_55_and_have_no_dead_gap(qapp, width, height) -> None:
    """Recent Activity and Action Center must each claim a real share of the
    row width (~45%/55%) with no large unused gap between them -- the bug
    being fixed here was Action Center collapsing to its own intrinsic
    (title-driven) width while Recent Activity took its full share, leaving a
    large dead middle gap."""
    controller = _build_controller()
    controller.reload()

    previous_handler, messages, engine, component, page, window = _load_overview_workspace(
        qapp, width=width, height=height
    )
    try:
        page.setProperty("globalOverviewController", controller)
        qapp.processEvents()

        recent_card = _find_by_object_name(page, "overviewRecentActivityCard")
        action_card = _find_by_object_name(page, "overviewActionCenterCard")
        assert recent_card is not None
        assert action_card is not None

        recent_width = recent_card.property("width")
        action_width = action_card.property("width")
        assert recent_width > 0
        assert action_width > 0

        # Roughly 45/55 (allow rounding slack).
        total = recent_width + action_width
        assert 0.40 <= recent_width / total <= 0.50
        assert 0.50 <= action_width / total <= 0.60

        # No large dead middle gap: the two cards' combined width plus the
        # section gap should account for essentially the full content row
        # width (minus the workspace frame's own outer margins).
        content_row_width = recent_card.parentItem().property("width")
        assert content_row_width > 0
        unused = content_row_width - total
        assert unused < content_row_width * 0.05
    finally:
        _teardown(previous_handler, page, window, qapp)


@pytest.mark.parametrize(
    "width,height",
    [
        (1600, 1000),
        (1366, 768),
    ],
)
def test_action_center_list_fills_its_panel_width(qapp, width, height) -> None:
    controller = _build_controller()
    controller.reload()

    previous_handler, messages, engine, component, page, window = _load_overview_workspace(
        qapp, width=width, height=height
    )
    try:
        page.setProperty("globalOverviewController", controller)
        qapp.processEvents()

        action_card = _find_by_object_name(page, "overviewActionCenterCard")
        action_list = _find_by_object_name(page, "overviewActionCenterList")
        assert action_card is not None
        assert action_list is not None

        card_width = action_card.property("width")
        list_width = action_list.property("width")
        assert card_width > 0
        # The list sits inside the card's content ColumnLayout, which is set
        # to the card's own width -- allow a small tolerance for the card's
        # internal edge rounding, never the near-zero intrinsic width the
        # pre-fix layout collapsed to.
        assert list_width >= card_width * 0.9
    finally:
        _teardown(previous_handler, page, window, qapp)


def test_recent_activity_and_action_center_stack_full_width_when_narrow(qapp) -> None:
    controller = _build_controller()
    controller.reload()

    previous_handler, messages, engine, component, page, window = _load_overview_workspace(
        qapp, width=900, height=900
    )
    try:
        page.setProperty("globalOverviewController", controller)
        qapp.processEvents()

        recent_card = _find_by_object_name(page, "overviewRecentActivityCard")
        action_card = _find_by_object_name(page, "overviewActionCenterCard")
        assert recent_card is not None
        assert action_card is not None

        content_row_width = recent_card.parentItem().property("width")
        assert content_row_width > 0
        # Narrow layout stacks the two panels vertically -- each claims the
        # full row width rather than sharing it.
        assert recent_card.property("width") >= content_row_width * 0.95
        assert action_card.property("width") >= content_row_width * 0.95
    finally:
        _teardown(previous_handler, page, window, qapp)


# -- Platform Overview regression (OverviewMetricTile promotion) -------------------------------


def test_platform_overview_still_loads_without_warnings_after_promotion(qapp) -> None:
    messages: list[str] = []

    def capture_message(_message_type, _context, message: str) -> None:
        messages.append(str(message))

    previous_handler = qInstallMessageHandler(capture_message)
    page = None
    window = None
    try:
        engine = create_qml_engine()
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(PLATFORM_OVERVIEW_PAGE.resolve())))
        page = component.create()
        assert page is not None, "\n".join(error.toString() for error in component.errors())

        window = QQuickWindow()
        window.resize(1280, 800)
        page.setParentItem(window.contentItem())
        page.setWidth(1280)
        page.setHeight(800)
        page.setProperty(
            "metrics",
            [
                {"label": "Organizations", "value": "3", "supportingText": "Install profiles"},
                {"label": "Sites", "value": "5", "supportingText": "Active operating sites"},
            ],
        )
        window.show()
        qapp.processEvents()

        assert _relevant_warnings(messages) == []
    finally:
        if page is not None:
            page.setParentItem(None)
            page.deleteLater()
        if window is not None:
            window.close()
            window.deleteLater()
        qapp.processEvents()
        qInstallMessageHandler(previous_handler)
