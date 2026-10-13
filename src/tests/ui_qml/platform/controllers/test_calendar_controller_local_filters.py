from __future__ import annotations

from dataclasses import dataclass

from src.ui_qml.platform.controllers.calendars.calendar_controller import (
    PlatformCalendarController,
)
from src.ui_qml.platform.view_models import (
    PlatformWorkspaceActionItemViewModel,
    PlatformWorkspaceActionListViewModel,
)


@dataclass
class _FakePresenter:
    items: tuple

    def build_catalog(self) -> PlatformWorkspaceActionListViewModel:
        return PlatformWorkspaceActionListViewModel(
            title="Calendars",
            subtitle="Operational working calendars for this organization.",
            empty_state="No calendars configured.",
            items=self.items,
        )


def _item(id_, *, title="Global Calendar", code="GLOBAL", is_active=True, calendar_type="GLOBAL"):
    return PlatformWorkspaceActionItemViewModel(
        id=id_,
        title=title,
        status_label="Active" if is_active else "Inactive",
        subtitle="Mon–Fri",
        supporting_text="",
        meta_text="",
        state={"code": code, "isActive": is_active, "calendarType": calendar_type},
    )


def _controller(items):
    controller = PlatformCalendarController(_FakePresenter(items=items))
    controller.refresh()
    return controller


def test_refresh_populates_the_full_unfiltered_list():
    controller = _controller((_item("cal-1"), _item("cal-2", title="Hamburg Site Calendar")))

    assert len(controller.calendars["items"]) == 2


def test_search_text_filters_by_title_case_insensitively():
    controller = _controller((_item("cal-1", title="Global Calendar"), _item("cal-2", title="Hamburg Site Calendar")))

    controller.setCalendarSearchText("hamburg")

    items = controller.calendars["items"]
    assert len(items) == 1
    assert items[0]["id"] == "cal-2"


def test_search_text_also_matches_calendar_code():
    controller = _controller((_item("cal-1", code="GLOBAL"), _item("cal-2", code="SITE-HH")))

    controller.setCalendarSearchText("site-hh")

    items = controller.calendars["items"]
    assert len(items) == 1
    assert items[0]["id"] == "cal-2"


def test_status_filter_narrows_to_active_or_inactive():
    controller = _controller((_item("cal-1", is_active=True), _item("cal-2", is_active=False)))

    controller.setCalendarStatusFilter("inactive")

    items = controller.calendars["items"]
    assert len(items) == 1
    assert items[0]["id"] == "cal-2"


def test_type_filter_narrows_to_the_selected_calendar_type():
    controller = _controller((_item("cal-1", calendar_type="GLOBAL"), _item("cal-2", calendar_type="SITE")))

    controller.setCalendarTypeFilter("SITE")

    items = controller.calendars["items"]
    assert len(items) == 1
    assert items[0]["id"] == "cal-2"


def test_filters_compose_together():
    controller = _controller((
        _item("cal-1", title="Hamburg Site Calendar", calendar_type="SITE", is_active=True),
        _item("cal-2", title="Hamburg Backup Calendar", calendar_type="SITE", is_active=False),
        _item("cal-3", title="Berlin Site Calendar", calendar_type="SITE", is_active=True),
    ))

    controller.setCalendarSearchText("hamburg")
    controller.setCalendarTypeFilter("SITE")
    controller.setCalendarStatusFilter("active")

    items = controller.calendars["items"]
    assert len(items) == 1
    assert items[0]["id"] == "cal-1"


def test_clearing_all_filters_restores_the_full_list():
    controller = _controller((_item("cal-1"), _item("cal-2", is_active=False)))
    controller.setCalendarStatusFilter("active")
    assert len(controller.calendars["items"]) == 1

    controller.setCalendarStatusFilter("")

    assert len(controller.calendars["items"]) == 2


def test_refresh_again_resets_the_cached_unfiltered_list():
    controller = _controller((
        _item("cal-1", title="Global Calendar"),
        _item("cal-2", title="Hamburg Site Calendar"),
    ))
    controller.setCalendarSearchText("hamburg")
    assert len(controller.calendars["items"]) == 1

    controller._presenter.items = (_item("cal-3", title="Berlin Site Calendar"),)
    controller.refresh()

    # The stale search text still applies to the freshly refreshed list.
    assert controller.calendars["items"] == []
