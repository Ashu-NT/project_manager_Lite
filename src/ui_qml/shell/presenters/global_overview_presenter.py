from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Generic, TypeVar

from src.core.application.global_overview.api.desktop.global_overview import (
    GlobalOverviewDesktopApi,
)
from src.core.application.global_overview.contracts.action_center import ActionCenterItemDto
from src.core.application.global_overview.contracts.module_summary import ModuleSummaryDto
from src.core.application.global_overview.contracts.overview import (
    GlobalOverviewCapabilitiesDto,
    GlobalOverviewContextDto,
)
from src.core.platform.api.desktop.history.activity.models.activity import ActivityEntryDto
from src.ui_qml.shell.view_models.global_overview import (
    ActionCenterRowViewModel,
    ActivityRowViewModel,
    AttentionCardViewModel,
    GlobalOverviewContextViewModel,
    ModuleCardViewModel,
    QuickActionViewModel,
    build_context_line,
)

logger = logging.getLogger(__name__)

_ResultT = TypeVar("_ResultT")

_CONTEXT_LOAD_ERROR = "Overview context could not be loaded."
_ATTENTION_LOAD_ERROR = "Attention summary could not be loaded."
_MODULES_LOAD_ERROR = "Modules could not be loaded."
_RECENT_ACTIVITY_LOAD_ERROR = "Recent activity could not be loaded."
_ACTION_CENTER_LOAD_ERROR = "Action items could not be loaded."
_QUICK_ACTIONS_LOAD_ERROR = "Quick actions could not be loaded."

_TASK_STATUS_LABELS = {
    "todo": "To do",
    "in_progress": "In progress",
    "blocked": "Blocked",
}
_MODULE_LABELS = {
    "platform": "Platform",
    "project_management": "Project Management",
}
# Action Center category filter keys, matching ActionCenterSummaryDto's own
# field names -- a future filtered Action Center view can pass one straight
# through without a separate translation table.
_ATTENTION_CARDS = (
    ("all", "All action items", "all_action_items"),
    ("reviews_and_approvals", "Reviews & approvals", "reviews_and_approvals"),
    ("assigned_work", "Assigned work", "assigned_work"),
    ("submissions", "Submissions", "submissions"),
)

_MAX_QUICK_ACTIONS = 4


@dataclass(frozen=True)
class _QuickActionCandidate:
    key: str
    label: str
    icon: str
    route_id: str
    required_permission: str
    # None means the action's own area is Platform-area, which has no
    # enable/license lifecycle and is never gated by accessible_module_codes
    # (see module_access_policy.py) -- only a real EnterpriseModule code
    # (e.g. "project_management") belongs here.
    required_module_code: str | None


# Each candidate below was individually verified against the real codebase:
# the exact permission code a command handler actually requires, the exact
# module-accessibility prerequisite (if any), and an existing, distinct,
# registered shell route -- never invented. "Create project" is the only
# candidate with all three verified as a distinct destination:
#   permission: ProjectService.create_project -> require_permission(...,
#       "project.manage") (projects/commands/lifecycle.py)
#   module: gated on "project_management" via accessible_module_codes
#   route: "project_management.projects", a real registered QmlRoute
# "Add user" (auth.manage), "Add department" (settings.manage), and
# "Review approvals" (approval.decide) each have a real, verified
# permission, but the shell currently registers only one single generic
# Platform route ("platform.workspace", see ui_qml/platform/routes.py) --
# there is no distinct navigable destination for any of them yet, so
# showing three different "actions" that all land on the same generic page
# would not be a genuine action, just generic navigation dressed up as one.
# They are deliberately omitted rather than invented; adding distinct
# Platform routes for them is a deferred capability, not implemented here.
_QUICK_ACTION_CANDIDATES = (
    _QuickActionCandidate(
        key="create_project",
        label="Create project",
        icon="project",
        route_id="project_management.projects",
        required_permission="project.manage",
        required_module_code="project_management",
    ),
)


@dataclass(frozen=True)
class SectionResult(Generic[_ResultT]):
    """A presenter section's outcome: either the mapped view-model data, or
    a business-friendly error message -- never a raw exception/DesktopApiResult
    error leaking through. `empty` marks a successful load with nothing to
    show (not an error)."""

    ok: bool
    data: _ResultT | None
    error_message: str | None = None
    empty: bool = False


class GlobalOverviewPresenter:
    """Pure Python presentation mapping for the Global Overview page.

    Each `load_*` method is independently callable and owns its own
    GlobalOverviewDesktopApi call -- one section failing never affects
    another. No QML/Qt objects, no ORM, no business-rule duplication: every
    accessibility/visibility/ordering decision was already made by the
    application layer: this class only maps already-decided data into
    display strings.
    """

    def __init__(self, *, api: GlobalOverviewDesktopApi) -> None:
        self._api = api

    def load_context(self) -> SectionResult:
        result = self._api.get_context()
        if not result.ok or result.data is None:
            self._log_failure("context", result)
            return SectionResult(ok=False, data=None, error_message=_CONTEXT_LOAD_ERROR)
        return SectionResult(ok=True, data=self._build_context(result.data))

    def load_attention(self) -> SectionResult:
        result = self._api.get_attention_summary()
        if not result.ok or result.data is None:
            self._log_failure("attention", result)
            return SectionResult(ok=False, data=None, error_message=_ATTENTION_LOAD_ERROR)
        summary = result.data
        cards = tuple(
            AttentionCardViewModel(
                key=key,
                label=label,
                value=getattr(summary, field_name),
                supporting_text=_attention_supporting_text(getattr(summary, field_name)),
                # No dedicated (filtered or full) Action Center destination
                # exists yet -- left empty rather than invented. See
                # AttentionCardViewModel's docstring.
                route_id="",
                filter_key=key,
                interactive=False,
            )
            for key, label, field_name in _ATTENTION_CARDS
        )
        # A successful Attention summary always produces these four cards,
        # even when every count is zero -- zero is a legitimate answer, not
        # an empty section (unlike Modules/Recent Activity/Action Center,
        # whose row count genuinely can be zero).
        return SectionResult(ok=True, data=cards, empty=False)

    def load_modules(self) -> SectionResult:
        result = self._api.list_module_summaries()
        if not result.ok or result.data is None:
            self._log_failure("modules", result)
            return SectionResult(ok=False, data=None, error_message=_MODULES_LOAD_ERROR)
        cards = tuple(_build_module_card(dto) for dto in result.data)
        return SectionResult(ok=True, data=cards, empty=not cards)

    def load_recent_activity(self, *, limit: int = 50) -> SectionResult:
        result = self._api.list_recent_activity(limit=limit)
        if not result.ok or result.data is None:
            self._log_failure("recent_activity", result)
            return SectionResult(ok=False, data=None, error_message=_RECENT_ACTIVITY_LOAD_ERROR)
        rows = tuple(_build_activity_row(entry) for entry in result.data)
        return SectionResult(ok=True, data=rows, empty=not rows)

    def load_action_center(self, *, limit: int = 50) -> SectionResult:
        result = self._api.list_action_center(limit=limit)
        if not result.ok or result.data is None:
            self._log_failure("action_center", result)
            return SectionResult(ok=False, data=None, error_message=_ACTION_CENTER_LOAD_ERROR)
        today = date.today()
        rows = tuple(_build_action_center_row(item, today=today) for item in result.data.items)
        return SectionResult(ok=True, data=rows, empty=not rows)

    def load_quick_actions(self) -> SectionResult:
        """Derives Quick Actions only from GlobalOverviewDesktopApi
        .get_capabilities() -- generic effective-permission and accessible-
        module inputs, never a role name, never a direct call to
        PlatformRuntimeApplicationService from this layer. See
        _QUICK_ACTION_CANDIDATES for exactly which actions were verified
        against the real codebase and which were deliberately omitted.
        """
        result = self._api.get_capabilities()
        if not result.ok or result.data is None:
            self._log_failure("quick_actions", result)
            return SectionResult(ok=False, data=None, error_message=_QUICK_ACTIONS_LOAD_ERROR)
        actions = _build_quick_actions(result.data)
        return SectionResult(ok=True, data=actions, empty=not actions)

    def _build_context(self, dto: GlobalOverviewContextDto) -> GlobalOverviewContextViewModel:
        return GlobalOverviewContextViewModel(
            tenant_name=dto.tenant_name,
            organization_name=dto.organization_name,
            role_label=dto.role_label,
            context_line=build_context_line(
                tenant_name=dto.tenant_name,
                organization_name=dto.organization_name,
                role_label=dto.role_label,
            ),
        )

    @staticmethod
    def _log_failure(section: str, result) -> None:
        error = getattr(result, "error", None)
        logger.error(
            "Global Overview section load failed section=%s code=%s message=%s",
            section,
            getattr(error, "code", None),
            getattr(error, "message", None),
        )


def _attention_supporting_text(value: int) -> str:
    noun = "item" if value == 1 else "items"
    return f"{value} {noun}"


def _build_module_card(dto: ModuleSummaryDto) -> ModuleCardViewModel:
    return ModuleCardViewModel(
        module_code=dto.module_code,
        title=dto.title,
        description=dto.description,
        icon_key=dto.module_code or "module",
        summary_text=dto.summary_text,
        route_id=dto.route_id,
    )


def _build_quick_actions(
    capabilities: GlobalOverviewCapabilitiesDto,
) -> tuple[QuickActionViewModel, ...]:
    actions: list[QuickActionViewModel] = []
    for candidate in _QUICK_ACTION_CANDIDATES:
        if candidate.required_permission not in capabilities.effective_permissions:
            continue
        if (
            candidate.required_module_code is not None
            and candidate.required_module_code not in capabilities.accessible_module_codes
        ):
            continue
        actions.append(
            QuickActionViewModel(
                key=candidate.key,
                label=candidate.label,
                icon=candidate.icon,
                route_id=candidate.route_id,
            )
        )
    return tuple(actions[:_MAX_QUICK_ACTIONS])


def _build_activity_row(entry: ActivityEntryDto) -> ActivityRowViewModel:
    return ActivityRowViewModel(
        id=entry.id,
        title=entry.human_message,
        # ActivityEntryDto only carries a raw actor_id, never a resolved
        # display name -- showing it as if it were a name would be
        # misleading, and this layer has no user-lookup input to resolve a
        # real one. Deferred: "Activity actor display-name resolution".
        actor_label=None,
        module_label=_MODULE_LABELS.get(entry.module, entry.module.replace("_", " ").title()),
        timestamp_label=entry.timestamp.strftime("%d %b %Y · %H:%M"),
        icon=entry.icon,
        color=entry.color,
        activity_type=entry.type,
    )


def _build_action_center_row(item: ActionCenterItemDto, *, today: date) -> ActionCenterRowViewModel:
    return ActionCenterRowViewModel(
        id=item.id,
        title=item.title,
        module_label=item.module,
        subject_display=item.subject_display,
        action_state=item.action_state,
        status_label=_status_label(item),
        priority_label=item.priority.replace("_", " ").title() if item.priority else None,
        # Generic on the DTO's own due_at, never gated on `kind` -- Task is
        # simply the only contributor with a real due_at today; a future
        # contributor providing one must get the same formatting for free.
        # Baseline/Approval/Timesheet always carry due_at=None from the
        # backend, so this never fabricates a date for them.
        due_label=_format_due_label(item.due_at, today=today),
        # Only a workspace-level route exists per item today -- no per-object
        # deep link is invented here (see routing limitation, item 13).
        route_id=item.route_id,
        kind=item.kind,
    )


def _status_label(item: ActionCenterItemDto) -> str:
    if item.kind == "pm_task":
        return _TASK_STATUS_LABELS.get(item.action_state, item.action_state.replace("_", " ").title())
    if item.kind == "baseline_review":
        return "Awaiting review"
    if item.kind == "approval":
        return "Awaiting decision"
    if item.kind == "timesheet":
        return "Rejected · Action required" if item.action_state == "rejected" else "Open"
    return item.action_state.replace("_", " ").title()


def _format_due_label(due_at: date | None, *, today: date) -> str | None:
    if due_at is None:
        return None
    delta_days = (due_at - today).days
    if delta_days == 0:
        return "Due today"
    if delta_days < 0:
        overdue_days = -delta_days
        noun = "day" if overdue_days == 1 else "days"
        return f"Overdue by {overdue_days} {noun}"
    return f"Due {due_at.day} {due_at:%b}"


__all__ = ["GlobalOverviewPresenter", "SectionResult"]
