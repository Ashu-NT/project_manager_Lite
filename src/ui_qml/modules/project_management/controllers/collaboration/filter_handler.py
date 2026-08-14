from __future__ import annotations


def _set_scope_value(controller, *, attribute: str, signal, value: str) -> None:
    normalized = (value or "").strip() or "all"
    if normalized == getattr(controller._filter_service, attribute):
        return
    setattr(controller._filter_service, attribute, normalized)
    signal.emit()
    controller._inbox_page = 1
    controller._mentions_page = 1
    controller.refresh()


def set_selected_project_id(controller, value: str) -> None:
    _set_scope_value(
        controller,
        attribute="selected_project_id",
        signal=controller.selectedProjectIdChanged,
        value=value,
    )


def set_selected_team_id(controller, value: str) -> None:
    _set_scope_value(
        controller,
        attribute="selected_team_id",
        signal=controller.selectedTeamIdChanged,
        value=value,
    )


def set_selected_period_key(controller, value: str) -> None:
    _set_scope_value(
        controller,
        attribute="selected_period_key",
        signal=controller.selectedPeriodKeyChanged,
        value=value,
    )


def set_selected_unread_key(controller, value: str) -> None:
    _set_scope_value(
        controller,
        attribute="selected_unread_key",
        signal=controller.selectedUnreadKeyChanged,
        value=value,
    )


def set_inbox_search_text(controller, text: str) -> None:
    normalized = (text or "").strip()
    if normalized == controller._filter_service.inbox_search_text:
        return
    controller._filter_service.inbox_search_text = normalized
    controller.inboxSearchTextChanged.emit()
    controller._inbox_page = 1
    controller.refresh()


def set_mentions_search_text(controller, text: str) -> None:
    normalized = (text or "").strip()
    if normalized == controller._filter_service.mentions_search_text:
        return
    controller._filter_service.mentions_search_text = normalized
    controller.mentionsSearchTextChanged.emit()
    controller._mentions_page = 1
    controller.refresh()


def set_inbox_page(controller, page: int) -> None:
    normalized = max(1, int(page or 1))
    if normalized == controller._inbox_page:
        return
    controller._inbox_page = normalized
    controller.refresh()


def set_inbox_page_size(controller, page_size: int) -> None:
    normalized = max(1, int(page_size or 25))
    if normalized == controller._inbox_page_size:
        return
    controller._inbox_page_size = normalized
    controller._inbox_page = 1
    controller.refresh()


def set_mentions_page(controller, page: int) -> None:
    normalized = max(1, int(page or 1))
    if normalized == controller._mentions_page:
        return
    controller._mentions_page = normalized
    controller.refresh()


def set_mentions_page_size(controller, page_size: int) -> None:
    normalized = max(1, int(page_size or 25))
    if normalized == controller._mentions_page_size:
        return
    controller._mentions_page_size = normalized
    controller._mentions_page = 1
    controller.refresh()


__all__ = [name for name in globals() if name.startswith("set_")]
