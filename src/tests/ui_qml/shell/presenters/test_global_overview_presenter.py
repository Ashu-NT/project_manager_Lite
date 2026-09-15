from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

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
from src.ui_qml.shell.presenters.global_overview_presenter import GlobalOverviewPresenter

class _FakeGlobalOverviewApi:
    def __init__(self) -> None:
        self.context_result = DesktopApiResult(
            ok=True,
            data=GlobalOverviewContextDto(
                tenant_name="TECHASH Enterprise", organization_name="Shell", role_label=None
            ),
        )
        self.attention_result = DesktopApiResult(
            ok=True, data=ActionCenterSummaryDto(0, 0, 0, 0)
        )
        self.modules_result = DesktopApiResult(ok=True, data=())
        self.recent_activity_result = DesktopApiResult(ok=True, data=())
        self.action_center_result = DesktopApiResult(
            ok=True, data=ActionCenterContribution(items=(), summary=ActionCenterSummaryDto(0, 0, 0, 0))
        )
        self.capabilities_result = DesktopApiResult(
            ok=True,
            data=GlobalOverviewCapabilitiesDto(
                effective_permissions=frozenset(), accessible_module_codes=()
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


def _presenter() -> tuple[GlobalOverviewPresenter, _FakeGlobalOverviewApi]:
    api = _FakeGlobalOverviewApi()
    return GlobalOverviewPresenter(api=api), api


def _action_item(
    *,
    kind: str,
    action_state: str,
    due_at: date | None = None,
    route_id: str = "project_management.tasks",
    priority: str | None = None,
) -> ActionCenterItemDto:
    return ActionCenterItemDto(
        id="item-1",
        kind=kind,
        title="Item title",
        module="Project Management",
        subject_type="task",
        subject_id="subject-1",
        subject_display="Subject",
        action_state=action_state,
        route_id=route_id,
        priority=priority,
        due_at=due_at,
        sort_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )


# -- Context ---------------------------------------------------------------------------


def test_load_context_maps_tenant_and_organization():
    presenter, _ = _presenter()

    result = presenter.load_context()

    assert result.ok is True
    assert result.data.tenant_name == "TECHASH Enterprise"
    assert result.data.organization_name == "Shell"
    assert result.data.context_line == "TECHASH Enterprise · Shell"


def test_load_context_role_none_produces_no_dangling_separator():
    presenter, _ = _presenter()

    result = presenter.load_context()

    assert result.data.role_label is None
    assert not result.data.context_line.endswith("·")
    assert "None" not in result.data.context_line


def test_load_context_with_role_label_appends_it():
    presenter, api = _presenter()
    api.context_result = DesktopApiResult(
        ok=True,
        data=GlobalOverviewContextDto(
            tenant_name="TECHASH Enterprise", organization_name="Shell", role_label="Administrator"
        ),
    )

    result = presenter.load_context()

    assert result.data.context_line == "TECHASH Enterprise · Shell · Administrator"


def test_load_context_does_not_substitute_user_display_name():
    """The presenter must never invent a role from anything other than the
    real role_label field -- there is no userDisplayName input at all here."""
    presenter, api = _presenter()

    result = presenter.load_context()

    assert result.data.role_label is None
    assert result.data.context_line == "TECHASH Enterprise · Shell"


def test_load_context_failure_returns_friendly_message():
    presenter, api = _presenter()
    api.context_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="TENANT_CONTEXT_REQUIRED", message="boom", category="conflict")
    )

    result = presenter.load_context()

    assert result.ok is False
    assert result.data is None
    assert result.error_message == "Overview context could not be loaded."
    assert "boom" not in result.error_message
    assert "TENANT_CONTEXT_REQUIRED" not in result.error_message


# -- Attention ---------------------------------------------------------------------------


def test_load_attention_maps_exact_four_cards_in_order():
    presenter, api = _presenter()
    api.attention_result = DesktopApiResult(ok=True, data=ActionCenterSummaryDto(12, 5, 4, 3))

    result = presenter.load_attention()

    assert result.ok is True
    assert [card.key for card in result.data] == [
        "all",
        "reviews_and_approvals",
        "assigned_work",
        "submissions",
    ]
    assert [card.value for card in result.data] == [12, 5, 4, 3]
    assert result.data[0].label == "All action items"
    assert result.data[1].label == "Reviews & approvals"
    assert result.data[2].label == "Assigned work"
    assert result.data[3].label == "Submissions"


def test_load_attention_all_zero_counts_still_produces_four_visible_cards_and_is_not_empty():
    presenter, api = _presenter()
    api.attention_result = DesktopApiResult(ok=True, data=ActionCenterSummaryDto(0, 0, 0, 0))

    result = presenter.load_attention()

    assert result.ok is True
    assert result.error_message is None
    assert result.empty is False
    assert len(result.data) == 4
    assert all(card.value == 0 for card in result.data)
    assert [card.key for card in result.data] == [
        "all",
        "reviews_and_approvals",
        "assigned_work",
        "submissions",
    ]


def test_load_attention_cards_are_not_interactive_and_carry_no_fake_route():
    """No dedicated Action Center destination exists yet -- cards must not
    pretend to be navigable."""
    presenter, _ = _presenter()

    result = presenter.load_attention()

    assert all(card.interactive is False for card in result.data)
    assert all(card.route_id == "" for card in result.data)


def test_load_attention_failure_returns_friendly_message():
    presenter, api = _presenter()
    api.attention_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="X", message="boom", category="domain")
    )

    result = presenter.load_attention()

    assert result.ok is False
    assert result.error_message == "Attention summary could not be loaded."


# -- Action Center -------------------------------------------------------------------------


def test_task_due_today_label():
    presenter, api = _presenter()
    today = date.today()
    item = _action_item(kind="pm_task", action_state="todo", due_at=today)
    api.action_center_result = DesktopApiResult(
        ok=True,
        data=ActionCenterContribution(items=(item,), summary=ActionCenterSummaryDto(1, 0, 1, 0)),
    )

    result = presenter.load_action_center()

    row = result.data[0]
    assert row.due_label == "Due today"
    assert row.status_label == "To do"


def test_task_overdue_label():
    presenter, api = _presenter()
    overdue_date = date.today() - timedelta(days=5)
    item = _action_item(kind="pm_task", action_state="in_progress", due_at=overdue_date)
    api.action_center_result = DesktopApiResult(
        ok=True,
        data=ActionCenterContribution(items=(item,), summary=ActionCenterSummaryDto(1, 0, 1, 0)),
    )

    result = presenter.load_action_center()

    assert result.data[0].due_label == "Overdue by 5 days"
    assert result.data[0].status_label == "In progress"


def test_task_future_due_label():
    presenter, api = _presenter()
    future_date = date.today() + timedelta(days=7)
    item = _action_item(kind="pm_task", action_state="blocked", due_at=future_date)
    api.action_center_result = DesktopApiResult(
        ok=True,
        data=ActionCenterContribution(items=(item,), summary=ActionCenterSummaryDto(1, 0, 1, 0)),
    )

    result = presenter.load_action_center()

    expected_label = f"Due {future_date.day} {future_date:%b}"
    assert result.data[0].due_label == expected_label
    assert result.data[0].status_label == "Blocked"


def test_task_with_no_due_at_has_no_due_label():
    presenter, api = _presenter()
    item = _action_item(kind="pm_task", action_state="todo", due_at=None)
    api.action_center_result = DesktopApiResult(
        ok=True,
        data=ActionCenterContribution(items=(item,), summary=ActionCenterSummaryDto(1, 0, 1, 0)),
    )

    result = presenter.load_action_center()

    assert result.data[0].due_label is None


def test_baseline_review_has_no_fabricated_due_label():
    presenter, api = _presenter()
    item = _action_item(kind="baseline_review", action_state="awaiting_review")
    api.action_center_result = DesktopApiResult(
        ok=True,
        data=ActionCenterContribution(items=(item,), summary=ActionCenterSummaryDto(1, 1, 0, 0)),
    )

    result = presenter.load_action_center()

    assert result.data[0].status_label == "Awaiting review"
    assert result.data[0].due_label is None


def test_approval_has_no_fabricated_due_label():
    presenter, api = _presenter()
    item = _action_item(kind="approval", action_state="awaiting_decision")
    api.action_center_result = DesktopApiResult(
        ok=True,
        data=ActionCenterContribution(items=(item,), summary=ActionCenterSummaryDto(1, 1, 0, 0)),
    )

    result = presenter.load_action_center()

    assert result.data[0].status_label == "Awaiting decision"
    assert result.data[0].due_label is None


def test_timesheet_open_label():
    presenter, api = _presenter()
    item = _action_item(kind="timesheet", action_state="open")
    api.action_center_result = DesktopApiResult(
        ok=True,
        data=ActionCenterContribution(items=(item,), summary=ActionCenterSummaryDto(1, 0, 0, 1)),
    )

    result = presenter.load_action_center()

    assert result.data[0].status_label == "Open"
    assert result.data[0].due_label is None


def test_timesheet_rejected_label():
    presenter, api = _presenter()
    item = _action_item(kind="timesheet", action_state="rejected")
    api.action_center_result = DesktopApiResult(
        ok=True,
        data=ActionCenterContribution(items=(item,), summary=ActionCenterSummaryDto(1, 0, 0, 1)),
    )

    result = presenter.load_action_center()

    assert result.data[0].status_label == "Rejected · Action required"
    assert result.data[0].due_label is None


def test_due_label_formatting_is_generic_and_not_gated_on_kind():
    """A future contributor kind other than pm_task must get the same
    legitimate due/overdue formatting for free if it ever carries a real
    due_at -- formatting must key off item.due_at, never item.kind."""
    presenter, api = _presenter()
    overdue_date = date.today() - timedelta(days=2)
    item = _action_item(kind="baseline_review", action_state="awaiting_review", due_at=overdue_date)
    api.action_center_result = DesktopApiResult(
        ok=True,
        data=ActionCenterContribution(items=(item,), summary=ActionCenterSummaryDto(1, 1, 0, 0)),
    )

    result = presenter.load_action_center()

    assert result.data[0].due_label == "Overdue by 2 days"
    # The status label is still governed by kind/action_state, independent
    # of due-label formatting.
    assert result.data[0].status_label == "Awaiting review"


def test_action_center_row_preserves_route_id():
    presenter, api = _presenter()
    item = _action_item(kind="approval", action_state="awaiting_decision", route_id="control_approvals")
    api.action_center_result = DesktopApiResult(
        ok=True,
        data=ActionCenterContribution(items=(item,), summary=ActionCenterSummaryDto(1, 1, 0, 0)),
    )

    result = presenter.load_action_center()

    assert result.data[0].route_id == "control_approvals"


def test_action_center_failure_returns_friendly_message():
    presenter, api = _presenter()
    api.action_center_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="X", message="boom", category="domain")
    )

    result = presenter.load_action_center()

    assert result.ok is False
    assert result.error_message == "Action items could not be loaded."


# -- Recent Activity -------------------------------------------------------------------------


def test_recent_activity_maps_dto_fields():
    presenter, api = _presenter()
    entry = ActivityEntryDto(
        id="a1",
        action="task.created",
        entity_type="task",
        entity_id="t1",
        actor_id="user-42",
        module="project_management",
        timestamp=datetime(2026, 9, 15, 14, 30, tzinfo=timezone.utc),
        type="info",
        human_message="Task created",
        icon="task",
        color="blue",
    )
    api.recent_activity_result = DesktopApiResult(ok=True, data=(entry,))

    result = presenter.load_recent_activity()

    assert result.ok is True
    row = result.data[0]
    assert row.title == "Task created"
    # actor_id is a raw internal id, never a resolved display name -- must
    # never be shown to the user as if it were one (deferred: "Activity
    # actor display-name resolution").
    assert row.actor_label is None
    assert row.module_label == "Project Management"
    assert row.icon == "task"
    assert row.color == "blue"
    assert row.activity_type == "info"
    assert "15 Sep 2026" in row.timestamp_label


def test_recent_activity_empty_is_not_an_error():
    presenter, _ = _presenter()

    result = presenter.load_recent_activity()

    assert result.ok is True
    assert result.empty is True
    assert result.data == ()


def test_recent_activity_failure_returns_friendly_message():
    presenter, api = _presenter()
    api.recent_activity_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="X", message="boom", category="domain")
    )

    result = presenter.load_recent_activity()

    assert result.ok is False
    assert result.error_message == "Recent activity could not be loaded."


# -- Modules -------------------------------------------------------------------------


def test_modules_mapped_and_order_preserved():
    presenter, api = _presenter()
    api.modules_result = DesktopApiResult(
        ok=True,
        data=(
            ModuleSummaryDto(
                module_code="platform",
                title="Platform",
                description="desc",
                summary_text="2 items require attention",
                route_id="platform",
            ),
            ModuleSummaryDto(
                module_code="project_management",
                title="Project Management",
                description="desc",
                summary_text="12 active projects",
                route_id="project_management",
            ),
        ),
    )

    result = presenter.load_modules()

    assert [card.module_code for card in result.data] == ["platform", "project_management"]


def test_modules_degraded_metric_still_mapped():
    presenter, api = _presenter()
    api.modules_result = DesktopApiResult(
        ok=True,
        data=(
            ModuleSummaryDto(
                module_code="platform",
                title="Platform",
                description="desc",
                summary_text="Shared administration and governance",
                route_id="platform",
            ),
        ),
    )

    result = presenter.load_modules()

    assert result.data[0].summary_text == "Shared administration and governance"


def test_modules_failure_returns_friendly_message():
    presenter, api = _presenter()
    api.modules_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="X", message="boom", category="domain")
    )

    result = presenter.load_modules()

    assert result.ok is False
    assert result.error_message == "Modules could not be loaded."


# -- Quick Actions -------------------------------------------------------------------------


def _capabilities(
    *, permissions: frozenset[str] = frozenset(), modules: tuple[str, ...] = ()
) -> GlobalOverviewCapabilitiesDto:
    return GlobalOverviewCapabilitiesDto(
        effective_permissions=permissions, accessible_module_codes=modules
    )


def test_quick_actions_is_empty_when_no_permissions_are_held():
    presenter, api = _presenter()
    api.capabilities_result = DesktopApiResult(ok=True, data=_capabilities())

    result = presenter.load_quick_actions()

    assert result.ok is True
    assert result.data == ()
    assert result.empty is True


def test_create_project_shown_when_permission_and_module_are_both_present():
    presenter, api = _presenter()
    api.capabilities_result = DesktopApiResult(
        ok=True,
        data=_capabilities(
            permissions=frozenset({"project.manage"}), modules=("project_management",)
        ),
    )

    result = presenter.load_quick_actions()

    assert result.ok is True
    assert result.empty is False
    assert [action.key for action in result.data] == ["create_project"]
    assert result.data[0].label == "Create project"
    assert result.data[0].route_id == "project_management.projects"


def test_create_project_omitted_when_permission_is_missing():
    """Permission alone drives visibility -- with the module accessible but
    no permission, the action must not appear."""
    presenter, api = _presenter()
    api.capabilities_result = DesktopApiResult(
        ok=True, data=_capabilities(permissions=frozenset(), modules=("project_management",))
    )

    result = presenter.load_quick_actions()

    assert result.data == ()
    assert result.empty is True


def test_create_project_omitted_when_project_management_is_not_accessible():
    """The PM action also requires project_management accessibility, even
    when the permission itself is held."""
    presenter, api = _presenter()
    api.capabilities_result = DesktopApiResult(
        ok=True,
        data=_capabilities(permissions=frozenset({"project.manage"}), modules=()),
    )

    result = presenter.load_quick_actions()

    assert result.data == ()
    assert result.empty is True


def test_quick_actions_failure_returns_friendly_message():
    presenter, api = _presenter()
    api.capabilities_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="X", message="boom", category="domain")
    )

    result = presenter.load_quick_actions()

    assert result.ok is False
    assert result.error_message == "Quick actions could not be loaded."


def test_presenter_never_imports_platform_runtime_directly():
    """Structural guard for the Quick Actions API gap: the presenter must
    not import PlatformRuntimeApplicationService to work around the missing
    permission/module input -- everything comes through get_capabilities()."""
    import ast
    import inspect

    from src.ui_qml.shell.presenters import global_overview_presenter

    tree = ast.parse(inspect.getsource(global_overview_presenter))
    imported_names = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "PlatformRuntimeApplicationService" not in imported_names


def test_quick_actions_never_check_role_names():
    """Structural guard: no candidate/derivation logic may reference role
    names -- visibility is permission- and module-driven only."""
    import inspect

    from src.ui_qml.shell.presenters import global_overview_presenter

    source = inspect.getsource(global_overview_presenter._build_quick_actions)
    assert "role_name" not in source
    assert "role ==" not in source
    assert "role_label" not in source
