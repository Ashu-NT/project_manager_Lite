from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.ui_qml.modules.project_management.presenters.financials.audit_builder import (
    build_finance_audit_collection,
)


def _entry(**overrides) -> SimpleNamespace:
    fields = dict(
        id="audit-1",
        timestamp=datetime(2026, 3, 5, 14, 30, tzinfo=timezone.utc),
        operation="project_budget.approve",
        entity_type="project_budget",
        actor_username="Finance Manager",
        severity="low",
        category="FINANCIAL",
        source="desktop",
        changed_fields=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _api_returning(*entries) -> MagicMock:
    api = MagicMock()
    api.list_recent.return_value = DesktopApiResult(ok=True, data=tuple(entries))
    return api


def test_returns_unavailable_collection_without_an_api() -> None:
    result = build_finance_audit_collection(None, project_id="project-1")

    assert result["items"] == []
    assert result["emptyState"] == "Finance audit events are unavailable for this project."


def test_maps_title_actor_and_timestamp_from_real_fields() -> None:
    api = _api_returning(_entry())

    result = build_finance_audit_collection(api, project_id="project-1")

    item = result["items"][0]
    assert item["title"] == "Project Budget Approve"
    assert item["actorDisplay"] == "Finance Manager"
    assert item["occurredAtLabel"] == "05 Mar 2026 14:30"


def test_low_severity_has_no_badge_and_neutral_tone() -> None:
    api = _api_returning(_entry(severity="low"))

    item = build_finance_audit_collection(api, project_id="project-1")["items"][0]

    assert item["tone"] == "neutral"
    assert item["statusLabel"] == ""


def test_critical_severity_gets_danger_tone_and_badge() -> None:
    api = _api_returning(_entry(severity="critical"))

    item = build_finance_audit_collection(api, project_id="project-1")["items"][0]

    assert item["tone"] == "danger"
    assert item["statusLabel"] == "Critical"


def test_falls_back_to_system_when_actor_is_missing() -> None:
    api = _api_returning(_entry(actor_username=""))

    item = build_finance_audit_collection(api, project_id="project-1")["items"][0]

    assert item["actorDisplay"] == "System"


def test_description_reports_changed_fields_when_present() -> None:
    api = _api_returning(
        _entry(changed_fields={"status": {"before": "draft", "after": "approved"}})
    )

    item = build_finance_audit_collection(api, project_id="project-1")["items"][0]

    assert item["description"] == "Recorded change: status: draft -> approved"
