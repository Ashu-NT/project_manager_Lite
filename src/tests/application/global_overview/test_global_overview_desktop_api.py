from __future__ import annotations

from datetime import datetime, timezone

from src.core.application.global_overview.api.desktop.global_overview import (
    GlobalOverviewDesktopApi,
)
from src.core.application.global_overview.contracts.action_center import (
    ActionCenterContribution,
    ActionCenterSummaryDto,
)
from src.core.application.global_overview.contracts.module_summary import ModuleSummaryDto
from src.core.application.global_overview.contracts.overview import GlobalOverviewContextDto
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.history.activity.activity_entry import ActivityEntry


class _FakeGlobalOverviewService:
    def __init__(self) -> None:
        self.get_context_result = GlobalOverviewContextDto(
            tenant_name="Acme", organization_name="Acme HQ", role_label=None
        )
        self.attention_summary_result = ActionCenterSummaryDto(1, 1, 0, 0)
        self.module_summaries_result: tuple[ModuleSummaryDto, ...] = (
            ModuleSummaryDto(
                module_code="platform",
                title="Platform",
                description="",
                summary_text="",
                route_id="platform",
            ),
        )
        self.action_center_result = ActionCenterContribution(
            items=(), summary=ActionCenterSummaryDto(0, 0, 0, 0)
        )
        self.recent_activity_result: tuple[ActivityEntry, ...] = ()
        self.raise_error: Exception | None = None
        self.last_action_center_limit: int | None = None
        self.last_activity_limit: int | None = None

    def get_context(self):
        self._maybe_raise()
        return self.get_context_result

    def get_attention_summary(self):
        self._maybe_raise()
        return self.attention_summary_result

    def list_module_summaries(self):
        self._maybe_raise()
        return self.module_summaries_result

    def list_action_center(self, *, limit: int = 50):
        self._maybe_raise()
        self.last_action_center_limit = limit
        return self.action_center_result

    def list_recent_activity(self, *, limit: int = 50):
        self._maybe_raise()
        self.last_activity_limit = limit
        return self.recent_activity_result

    def _maybe_raise(self):
        if self.raise_error is not None:
            raise self.raise_error


def _api(service: _FakeGlobalOverviewService) -> GlobalOverviewDesktopApi:
    return GlobalOverviewDesktopApi(global_overview_service=service)


def test_get_context_returns_ok_result_on_success():
    service = _FakeGlobalOverviewService()

    result = _api(service).get_context()

    assert result.ok is True
    assert result.data == service.get_context_result


def test_get_context_wraps_business_rule_error():
    service = _FakeGlobalOverviewService()
    service.raise_error = BusinessRuleError("no scope", code="TENANT_CONTEXT_REQUIRED")

    result = _api(service).get_context()

    assert result.ok is False
    assert result.error.code == "TENANT_CONTEXT_REQUIRED"


def test_get_attention_summary_returns_ok_result():
    service = _FakeGlobalOverviewService()

    result = _api(service).get_attention_summary()

    assert result.ok is True
    assert result.data == ActionCenterSummaryDto(1, 1, 0, 0)


def test_list_module_summaries_returns_ok_result():
    service = _FakeGlobalOverviewService()

    result = _api(service).list_module_summaries()

    assert result.ok is True
    assert result.data == service.module_summaries_result


def test_list_action_center_passes_through_the_requested_limit():
    service = _FakeGlobalOverviewService()

    result = _api(service).list_action_center(limit=25)

    assert result.ok is True
    assert service.last_action_center_limit == 25


def test_list_recent_activity_serializes_entries_and_passes_through_limit():
    service = _FakeGlobalOverviewService()
    service.recent_activity_result = (
        ActivityEntry(
            id="a1",
            action="task.created",
            entity_type="task",
            entity_id="t1",
            actor_id="u1",
            actor_role=None,
            module="project_management",
            workspace_id=None,
            tenant_id="tenant-1",
            organization_id="org-1",
            timestamp=datetime(2026, 9, 1, tzinfo=timezone.utc),
            type="info",
            human_message="Task created",
        ),
    )

    result = _api(service).list_recent_activity(limit=30)

    assert result.ok is True
    assert service.last_activity_limit == 30
    assert len(result.data) == 1
    assert result.data[0].id == "a1"
    assert result.data[0].module == "project_management"


def test_each_desktop_api_method_is_independently_callable_when_another_fails():
    service = _FakeGlobalOverviewService()
    service.raise_error = RuntimeError("recent activity dependency exploded")

    # list_recent_activity fails and propagates (not a DomainError, so it is not
    # translated into a failed DesktopApiResult by execute_desktop_operation).
    import pytest

    with pytest.raises(RuntimeError):
        _api(service).list_recent_activity()

    # A fresh call with the dependency healthy again still succeeds -- proving
    # each method call is independent, not backed by shared build state.
    service.raise_error = None
    result = _api(service).get_attention_summary()
    assert result.ok is True
