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
from src.core.application.global_overview.contracts.overview import GlobalOverviewContextDto
from src.core.platform.api.desktop.history.activity.models.activity import ActivityEntryDto
from src.ui_qml.shell.view_models.global_overview import (
    ActionCenterRowViewModel,
    ActivityRowViewModel,
    AttentionCardViewModel,
    GlobalOverviewContextViewModel,
    ModuleCardViewModel,
    build_context_line,
)

logger = logging.getLogger(__name__)

_ResultT = TypeVar("_ResultT")

_CONTEXT_LOAD_ERROR = "Overview context could not be loaded."
_ATTENTION_LOAD_ERROR = "Attention summary could not be loaded."
_MODULES_LOAD_ERROR = "Modules could not be loaded."
_RECENT_ACTIVITY_LOAD_ERROR = "Recent activity could not be loaded."
_ACTION_CENTER_LOAD_ERROR = "Action items could not be loaded."

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
                # No dedicated Action Center route exists yet (see routing
                # limitation, item 13) -- left empty rather than invented.
                route_id="",
                filter_key=key,
            )
            for key, label, field_name in _ATTENTION_CARDS
        )
        return SectionResult(ok=True, data=cards)

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
        """Always returns an empty, non-error section.

        GlobalOverviewDesktopApi does not currently expose the effective-
        permission / accessible-module inputs Quick Actions would need to
        decide which actions to show without hardcoding role-name checks
        (see Phase 6D item 9/17). Rather than reach around the Desktop API
        boundary to PlatformRuntimeApplicationService directly, Quick
        Actions stays empty until that API surface is extended.
        """
        return SectionResult(ok=True, data=(), empty=True)

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


def _build_activity_row(entry: ActivityEntryDto) -> ActivityRowViewModel:
    return ActivityRowViewModel(
        id=entry.id,
        title=entry.human_message,
        # ActivityEntryDto only carries actor_id, not a resolved display
        # name -- this layer has no user-lookup input to resolve one, so
        # the raw id is shown rather than a fabricated name.
        actor_label=entry.actor_id or "",
        module_label=_MODULE_LABELS.get(entry.module, entry.module.replace("_", " ").title()),
        timestamp_label=entry.timestamp.strftime("%d %b %Y · %H:%M"),
        icon=entry.icon,
        color=entry.color,
        activity_type=entry.type,
    )


def _build_action_center_row(item: ActionCenterItemDto, *, today: date) -> ActionCenterRowViewModel:
    status_label, due_label = _status_and_due_label(item, today=today)
    return ActionCenterRowViewModel(
        id=item.id,
        title=item.title,
        module_label=item.module,
        subject_display=item.subject_display,
        action_state=item.action_state,
        status_label=status_label,
        priority_label=item.priority.replace("_", " ").title() if item.priority else None,
        due_label=due_label,
        # Only a workspace-level route exists per item today -- no per-object
        # deep link is invented here (see routing limitation, item 13).
        route_id=item.route_id,
        kind=item.kind,
    )


def _status_and_due_label(item: ActionCenterItemDto, *, today: date) -> tuple[str, str | None]:
    if item.kind == "pm_task":
        return _TASK_STATUS_LABELS.get(
            item.action_state, item.action_state.replace("_", " ").title()
        ), _format_due_label(item.due_at, today=today)
    if item.kind == "baseline_review":
        return "Awaiting review", None
    if item.kind == "approval":
        return "Awaiting decision", None
    if item.kind == "timesheet":
        if item.action_state == "rejected":
            return "Rejected · Action required", None
        return "Open", None
    return item.action_state.replace("_", " ").title(), None


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
