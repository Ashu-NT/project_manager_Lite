from __future__ import annotations

from .panel_row_builder import (
    build_approvals_rows,
    build_inbox_rows,
    build_mentions_rows,
)


def set_overview(controller, overview: dict[str, object]) -> None:
    if overview == controller._overview:
        return
    controller._overview = overview
    controller.overviewChanged.emit()


def set_inbox(controller, inbox: dict[str, object]) -> None:
    if inbox == controller._inbox:
        return
    controller._inbox = inbox
    controller._table_models.inbox.set_rows(build_inbox_rows(controller._inbox))
    controller.inboxChanged.emit()


def set_context(controller, context: dict[str, object]) -> None:
    if context == controller._context:
        return
    controller._context = context
    controller.contextChanged.emit()


def set_panel_tabs(controller, panel_tabs: list[dict[str, object]]) -> None:
    if panel_tabs == controller._panel_tabs:
        return
    controller._panel_tabs = panel_tabs
    controller.panelTabsChanged.emit()


def set_mentions(controller, mentions: dict[str, object]) -> None:
    if mentions == controller._mentions:
        return
    controller._mentions = mentions
    controller._table_models.mentions.set_rows(build_mentions_rows(controller._mentions))
    controller.mentionsChanged.emit()


def set_approvals(controller, approvals: dict[str, object]) -> None:
    if approvals == controller._approvals:
        return
    controller._approvals = approvals
    controller._table_models.approvals.set_rows(build_approvals_rows(controller._approvals))
    controller.approvalsChanged.emit()


def set_activity_feed(controller, activity_feed: dict[str, object]) -> None:
    if activity_feed == controller._activity_feed:
        return
    controller._activity_feed = activity_feed
    controller.activityFeedChanged.emit()


def set_selected_item_detail(
    controller, selected_item_detail: dict[str, object]
) -> None:
    if selected_item_detail == controller._selected_item_detail:
        return
    controller._selected_item_detail = selected_item_detail
    related = (
        selected_item_detail.get("relatedItems")
        if isinstance(selected_item_detail, dict)
        else {}
    )
    controller._table_models.related_items.set_rows(
        related.get("items", []) if isinstance(related, dict) else []
    )
    controller.selectedItemDetailChanged.emit()


__all__ = [
    "set_activity_feed",
    "set_approvals",
    "set_context",
    "set_inbox",
    "set_mentions",
    "set_overview",
    "set_panel_tabs",
    "set_selected_item_detail",
]
