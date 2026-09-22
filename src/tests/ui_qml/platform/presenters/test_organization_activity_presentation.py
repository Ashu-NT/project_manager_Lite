from __future__ import annotations

from datetime import datetime, timezone

from src.core.platform.api.desktop.history.activity.models.activity import ActivityEntryDto
from src.ui_qml.platform.presenters.organizations.organization_catalog_presenter import (
    PlatformOrganizationCatalogPresenter,
)


class _FakeActivityApi:
    def __init__(self, entries) -> None:
        self._entries = entries
        self.calls: list[tuple[str, int]] = []

    def list_for_organization_overview(self, organization_id: str, *, limit: int = 5, entity_types=None):
        self.calls.append((organization_id, limit))
        return tuple(self._entries)


def _entry(**overrides) -> ActivityEntryDto:
    fields = dict(
        id="a1",
        action="party.create",
        entity_type="party",
        entity_id="p1",
        actor_id="u1",
        module="platform",
        timestamp=datetime(2026, 3, 5, 14, 30, tzinfo=timezone.utc),
        type="info",
        human_message="Party created — Acme Corp",
        details={},
        icon=None,
        color=None,
        visibility="workspace",
    )
    fields.update(overrides)
    return ActivityEntryDto(**fields)


def test_build_recent_activity_serializes_to_the_canonical_presentation_shape() -> None:
    api = _FakeActivityApi([_entry()])
    presenter = PlatformOrganizationCatalogPresenter(activity_api=api)

    items = presenter.build_recent_activity("org-1", limit=25)

    assert len(items) == 1
    item = items[0]
    assert item["title"] == "Party created — Acme Corp"
    assert item["occurredAtLabel"] == "2026-03-05 14:30 UTC"
    assert item["occurredAt"] == "2026-03-05T14:30:00+00:00"
    assert item["tone"] == "success"
    assert "icon" not in item
    assert item["iconKey"] == "party"


def test_build_recent_activity_prefers_entry_icon_over_entity_type_default() -> None:
    api = _FakeActivityApi([_entry(icon="organization")])
    presenter = PlatformOrganizationCatalogPresenter(activity_api=api)

    items = presenter.build_recent_activity("org-1")
    assert items[0]["iconKey"] == "organization"


def test_build_recent_activity_falls_back_to_humanized_action_without_human_message() -> None:
    api = _FakeActivityApi([_entry(human_message="", action="employee.deactivate", entity_type="employee")])
    presenter = PlatformOrganizationCatalogPresenter(activity_api=api)

    items = presenter.build_recent_activity("org-1")
    assert items[0]["title"] == "Employee Deactivate"


def test_build_recent_activity_passes_the_requested_limit_through() -> None:
    api = _FakeActivityApi([])
    presenter = PlatformOrganizationCatalogPresenter(activity_api=api)

    presenter.build_recent_activity("org-1", limit=25)
    assert api.calls == [("org-1", 25)]


def test_build_detail_context_uses_a_five_item_preview_limit() -> None:
    api = _FakeActivityApi([_entry()])
    presenter = PlatformOrganizationCatalogPresenter(activity_api=api)

    context = presenter.build_detail_context("org-1")

    assert api.calls == [("org-1", 5)]
    assert len(context["recentActivity"]) == 1


def test_build_recent_activity_with_no_api_configured_returns_empty() -> None:
    presenter = PlatformOrganizationCatalogPresenter(activity_api=None)
    assert presenter.build_recent_activity("org-1") == []
