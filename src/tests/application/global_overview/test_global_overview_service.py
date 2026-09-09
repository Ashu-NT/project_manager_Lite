from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.core.application.global_overview.contracts.action_center import (
    ActionCenterContribution,
    ActionCenterSummaryDto,
)
from src.core.application.global_overview.contracts.module_summary import ModuleSummaryDto
from src.core.application.global_overview.services.global_overview_service import (
    GlobalOverviewService,
)
from src.core.platform.common.exceptions import BusinessRuleError

_TENANT_ID = "tenant-1"
_ORG_ID = "org-1"
_USER_ID = "user-1"


class _FakeScope:
    def __init__(self, *, tenant_name: str, organization_name: str) -> None:
        self.tenant_id = _TENANT_ID
        self.organization_id = _ORG_ID
        self.tenant = SimpleNamespace(display_name=tenant_name)
        self.organization = SimpleNamespace(display_name=organization_name)


class _FakeTenantContextService:
    def __init__(self, *, scope: _FakeScope | None = None) -> None:
        self._scope = scope or _FakeScope(tenant_name="Acme", organization_name="Acme HQ")

    def require_organization_context(self, *, operation_label: str) -> _FakeScope:
        return self._scope


class _FakePlatformRuntimeApplicationService:
    def __init__(self, *, accessible_codes: frozenset[str] = frozenset()) -> None:
        self._accessible_codes = accessible_codes

    def list_accessible_modules(self):
        return tuple(SimpleNamespace(code=code) for code in self._accessible_codes)


class _FakeActivityService:
    def __init__(self, *, entries=None, error: Exception | None = None) -> None:
        self._entries = entries or []
        self._error = error

    def list_recent(self, limit: int = 50):
        if self._error is not None:
            raise self._error
        return list(self._entries)


class _FakeActionCenterService:
    def __init__(self, *, contribution: ActionCenterContribution) -> None:
        self._contribution = contribution
        self.calls: list[int] = []

    def build(self, context, *, preview_limit: int = 50, today=None) -> ActionCenterContribution:
        self.calls.append(preview_limit)
        return self._contribution


class _FakeUserSession:
    def __init__(self, *, user_id: str | None = _USER_ID) -> None:
        self.principal = SimpleNamespace(user_id=user_id) if user_id is not None else None


def _entry(module: str, entry_id: str = "e1"):
    return SimpleNamespace(id=entry_id, module=module)


def _summary_dto(module_code: str) -> ModuleSummaryDto:
    return ModuleSummaryDto(
        module_code=module_code,
        title=module_code,
        description="",
        summary_text="",
        route_id=module_code,
    )


def _build_service(
    *,
    tenant_context_service=None,
    platform_runtime_application_service=None,
    activity_service=None,
    action_center_service=None,
    module_summary_contributors=(),
    user_session=None,
) -> GlobalOverviewService:
    return GlobalOverviewService(
        tenant_context_service=tenant_context_service or _FakeTenantContextService(),
        platform_runtime_application_service=(
            platform_runtime_application_service or _FakePlatformRuntimeApplicationService()
        ),
        activity_service=activity_service or _FakeActivityService(),
        action_center_service=action_center_service
        or _FakeActionCenterService(
            contribution=ActionCenterContribution(
                items=(), summary=ActionCenterSummaryDto(0, 0, 0, 0)
            )
        ),
        module_summary_contributors=module_summary_contributors,
        user_session=user_session or _FakeUserSession(),
    )


# -- Context ---------------------------------------------------------------------------


def test_get_context_maps_tenant_and_organization_display_names():
    scope = _FakeScope(tenant_name="Contoso", organization_name="Contoso West")
    service = _build_service(tenant_context_service=_FakeTenantContextService(scope=scope))

    context = service.get_context()

    assert context.tenant_name == "Contoso"
    assert context.organization_name == "Contoso West"


def test_get_context_role_label_is_always_none():
    service = _build_service()

    context = service.get_context()

    assert context.role_label is None


# -- Attention summary -------------------------------------------------------------------


def test_get_attention_summary_delegates_to_action_center_service_with_preview_limit_zero():
    action_center_service = _FakeActionCenterService(
        contribution=ActionCenterContribution(
            items=(), summary=ActionCenterSummaryDto(4, 1, 2, 1)
        )
    )
    service = _build_service(action_center_service=action_center_service)

    summary = service.get_attention_summary()

    assert summary == ActionCenterSummaryDto(4, 1, 2, 1)
    assert action_center_service.calls == [0]


# -- Action Center preview -----------------------------------------------------------------


def test_list_action_center_delegates_with_the_requested_limit():
    action_center_service = _FakeActionCenterService(
        contribution=ActionCenterContribution(
            items=(), summary=ActionCenterSummaryDto(0, 0, 0, 0)
        )
    )
    service = _build_service(action_center_service=action_center_service)

    service.list_action_center(limit=17)

    assert action_center_service.calls == [17]


# -- Module summaries ----------------------------------------------------------------------


def test_list_module_summaries_omits_none_contributors():
    class _NoneContributor:
        def get_summary(self, context):
            return None

    class _RealContributor:
        def get_summary(self, context):
            return _summary_dto("platform")

    service = _build_service(module_summary_contributors=(_NoneContributor(), _RealContributor()))

    summaries = service.list_module_summaries()

    assert [s.module_code for s in summaries] == ["platform"]


def test_module_summary_contributor_registration_order_does_not_affect_result():
    class _Contributor:
        def __init__(self, code: str) -> None:
            self._code = code

        def get_summary(self, context):
            return _summary_dto(self._code)

    platform = _Contributor("platform")
    pm = _Contributor("project_management")

    forward = _build_service(module_summary_contributors=(platform, pm)).list_module_summaries()
    backward = _build_service(module_summary_contributors=(pm, platform)).list_module_summaries()

    assert [s.module_code for s in forward] == [s.module_code for s in backward]


def test_a_failing_module_summary_contributor_is_omitted_without_breaking_others():
    class _FailingContributor:
        def get_summary(self, context):
            raise RuntimeError("accessibility determination blew up")

    class _WorkingContributor:
        def get_summary(self, context):
            return _summary_dto("project_management")

    service = _build_service(
        module_summary_contributors=(_FailingContributor(), _WorkingContributor())
    )

    summaries = service.list_module_summaries()

    assert [s.module_code for s in summaries] == ["project_management"]


# -- Recent activity -------------------------------------------------------------------------


def test_platform_activity_is_visible_regardless_of_accessible_modules():
    service = _build_service(
        activity_service=_FakeActivityService(entries=[_entry("platform")]),
        platform_runtime_application_service=_FakePlatformRuntimeApplicationService(
            accessible_codes=frozenset()
        ),
    )

    entries = service.list_recent_activity()

    assert [e.module for e in entries] == ["platform"]


def test_accessible_enterprise_module_activity_is_visible():
    service = _build_service(
        activity_service=_FakeActivityService(entries=[_entry("project_management")]),
        platform_runtime_application_service=_FakePlatformRuntimeApplicationService(
            accessible_codes=frozenset({"project_management"})
        ),
    )

    entries = service.list_recent_activity()

    assert [e.module for e in entries] == ["project_management"]


def test_inaccessible_enterprise_module_activity_is_excluded():
    service = _build_service(
        activity_service=_FakeActivityService(entries=[_entry("project_management")]),
        platform_runtime_application_service=_FakePlatformRuntimeApplicationService(
            accessible_codes=frozenset()
        ),
    )

    entries = service.list_recent_activity()

    assert entries == ()


def test_unknown_module_activity_fails_closed():
    service = _build_service(
        activity_service=_FakeActivityService(entries=[_entry("qhse")]),
        platform_runtime_application_service=_FakePlatformRuntimeApplicationService(
            accessible_codes=frozenset()
        ),
    )

    entries = service.list_recent_activity()

    assert entries == ()


# -- Independent failure boundaries ---------------------------------------------------------


def test_activity_failure_does_not_prevent_attention_module_or_action_center_calls():
    action_center_service = _FakeActionCenterService(
        contribution=ActionCenterContribution(
            items=(), summary=ActionCenterSummaryDto(1, 1, 0, 0)
        )
    )

    class _Contributor:
        def get_summary(self, context):
            return _summary_dto("platform")

    service = _build_service(
        activity_service=_FakeActivityService(error=RuntimeError("activity store unavailable")),
        action_center_service=action_center_service,
        module_summary_contributors=(_Contributor(),),
    )

    with pytest.raises(RuntimeError):
        service.list_recent_activity()

    assert service.get_attention_summary() == ActionCenterSummaryDto(1, 1, 0, 0)
    assert [s.module_code for s in service.list_module_summaries()] == ["platform"]
    assert service.list_action_center(limit=10).summary == ActionCenterSummaryDto(1, 1, 0, 0)


def test_action_center_context_requires_an_authenticated_principal():
    service = _build_service(user_session=_FakeUserSession(user_id=None))

    with pytest.raises(BusinessRuleError) as exc:
        service.get_attention_summary()
    assert exc.value.code == "AUTHENTICATION_REQUIRED"
