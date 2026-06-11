from __future__ import annotations

from .panel_row_builder import (
    build_approvals_rows,
    build_inbox_rows,
    build_mentions_rows,
    build_team_updates_rows,
)


def set_selected_project_id(controller, value: str) -> None:
    v = (value or "").strip() or "all"
    if v == controller._filter_service.selected_project_id:
        return
    controller._filter_service.selected_project_id = v
    controller.selectedProjectIdChanged.emit()
    rebuild_all_panel_models(controller)


def set_selected_team_id(controller, value: str) -> None:
    v = (value or "").strip() or "all"
    if v == controller._filter_service.selected_team_id:
        return
    controller._filter_service.selected_team_id = v
    controller.selectedTeamIdChanged.emit()
    rebuild_all_panel_models(controller)


def set_selected_period_key(controller, value: str) -> None:
    v = (value or "").strip() or "all"
    if v == controller._filter_service.selected_period_key:
        return
    controller._filter_service.selected_period_key = v
    controller.selectedPeriodKeyChanged.emit()
    rebuild_all_panel_models(controller)


def set_selected_unread_key(controller, value: str) -> None:
    v = (value or "").strip() or "all"
    if v == controller._filter_service.selected_unread_key:
        return
    controller._filter_service.selected_unread_key = v
    controller.selectedUnreadKeyChanged.emit()
    rebuild_all_panel_models(controller)


def set_inbox_search_text(controller, text: str) -> None:
    v = (text or "").strip()
    if v == controller._filter_service.inbox_search_text:
        return
    controller._filter_service.inbox_search_text = v
    controller.inboxSearchTextChanged.emit()
    controller._table_models.inbox.set_rows(
        build_inbox_rows(controller._notifications, controller._filter_service)
    )


def set_mentions_search_text(controller, text: str) -> None:
    v = (text or "").strip()
    if v == controller._filter_service.mentions_search_text:
        return
    controller._filter_service.mentions_search_text = v
    controller.mentionsSearchTextChanged.emit()
    controller._table_models.mentions.set_rows(
        build_mentions_rows(controller._mentions, controller._filter_service)
    )


def set_approvals_search_text(controller, text: str) -> None:
    v = (text or "").strip()
    if v == controller._filter_service.approvals_search_text:
        return
    controller._filter_service.approvals_search_text = v
    controller.approvalsSearchTextChanged.emit()
    controller._table_models.approvals.set_rows(
        build_approvals_rows(controller._approvals, controller._filter_service)
    )


def set_team_updates_search_text(controller, text: str) -> None:
    v = (text or "").strip()
    if v == controller._filter_service.team_updates_search_text:
        return
    controller._filter_service.team_updates_search_text = v
    controller.teamUpdatesSearchTextChanged.emit()
    controller._table_models.team_updates.set_rows(
        build_team_updates_rows(controller._team_updates, controller._filter_service)
    )


def rebuild_all_panel_models(controller) -> None:
    controller._table_models.inbox.set_rows(
        build_inbox_rows(controller._notifications, controller._filter_service)
    )
    controller._table_models.mentions.set_rows(
        build_mentions_rows(controller._mentions, controller._filter_service)
    )
    controller._table_models.approvals.set_rows(
        build_approvals_rows(controller._approvals, controller._filter_service)
    )
    controller._table_models.team_updates.set_rows(
        build_team_updates_rows(controller._team_updates, controller._filter_service)
    )


__all__ = [
    "rebuild_all_panel_models",
    "set_approvals_search_text",
    "set_inbox_search_text",
    "set_mentions_search_text",
    "set_selected_period_key",
    "set_selected_project_id",
    "set_selected_team_id",
    "set_selected_unread_key",
    "set_team_updates_search_text",
]
