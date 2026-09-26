from __future__ import annotations

from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationDto,
)
from src.core.platform.api.desktop.models.common import (
    DesktopApiError,
    DesktopApiResult,
)
from src.core.platform.domain.master_data.org import (
    ORGANIZATION_STATUS_ACTIVE,
    ORGANIZATION_STATUS_INACTIVE,
)
from src.ui_qml.shell.controllers.organization.organization_switcher_controller import (
    OrganizationSwitcherController,
)
from src.ui_qml.shell.presenters.organization.organization_switcher_presenter import (
    OrganizationSwitcherPresenter,
)


def _org(id_: str, *, name: str, enabled: bool = True) -> OrganizationDto:
    return OrganizationDto(
        id=id_,
        organization_code=id_.upper(),
        display_name=name,
        timezone_name="UTC",
        base_currency="USD",
        status=ORGANIZATION_STATUS_ACTIVE if enabled else ORGANIZATION_STATUS_INACTIVE,
        version=1,
    )


class _FakeTenantApi:
    def __init__(self, *, organizations, active_id: str) -> None:
        self._organizations = organizations
        self._active_id = active_id
        self.switch_result: DesktopApiResult | None = None
        self.last_switch_id: str | None = None

    def list_accessible_organizations(self):
        return DesktopApiResult(ok=True, data=tuple(self._organizations))

    def get_active_organization(self):
        active = next((o for o in self._organizations if o.id == self._active_id), None)
        return DesktopApiResult(ok=True, data=active)

    def switch_to_organization(self, organization_id: str):
        self.last_switch_id = organization_id
        if self.switch_result is not None:
            return self.switch_result
        self._active_id = organization_id
        target = next(o for o in self._organizations if o.id == organization_id)
        return DesktopApiResult(ok=True, data=target)


def _controller(api) -> OrganizationSwitcherController:
    return OrganizationSwitcherController(presenter=OrganizationSwitcherPresenter(tenant_api=api))


# -- one accessible organization -------------------------------------------------------------


def test_single_accessible_organization_is_not_multi():
    api = _FakeTenantApi(organizations=[_org("org-1", name="Only Org")], active_id="org-1")
    controller = _controller(api)

    controller.refresh()

    assert controller.isMultiOrganization is False
    assert controller.activeOrganizationId == "org-1"
    assert len(controller.organizations) == 1


# -- multiple organizations -------------------------------------------------------------------


def test_multiple_organizations_is_multi():
    api = _FakeTenantApi(
        organizations=[_org("org-1", name="Org One"), _org("org-2", name="Org Two")],
        active_id="org-1",
    )
    controller = _controller(api)

    controller.refresh()

    assert controller.isMultiOrganization is True
    assert [o["id"] for o in controller.organizations] == ["org-1", "org-2"]


# -- successful switch -------------------------------------------------------------------


def test_successful_switch_updates_active_id_and_emits_organization_switched():
    api = _FakeTenantApi(
        organizations=[_org("org-1", name="Org One"), _org("org-2", name="Org Two")],
        active_id="org-1",
    )
    controller = _controller(api)
    controller.refresh()

    emitted = []
    controller.organizationSwitched.connect(lambda: emitted.append(1))

    ok = controller.switchToOrganization("org-2")

    assert ok is True
    assert controller.activeOrganizationId == "org-2"
    assert emitted == [1]
    assert controller.errorMessage == ""


# -- failed switch -------------------------------------------------------------------


def test_failed_switch_does_not_emit_and_sets_error_message():
    api = _FakeTenantApi(
        organizations=[_org("org-1", name="Org One"), _org("org-2", name="Org Two")],
        active_id="org-1",
    )
    api.switch_result = DesktopApiResult(
        ok=False, error=DesktopApiError(code="X", message="Cannot switch.", category="conflict")
    )
    controller = _controller(api)
    controller.refresh()

    emitted = []
    controller.organizationSwitched.connect(lambda: emitted.append(1))

    ok = controller.switchToOrganization("org-2")

    assert ok is False
    assert emitted == []
    assert controller.activeOrganizationId == "org-1"
    assert controller.errorMessage == "Cannot switch."


def test_switch_with_empty_id_is_a_no_op():
    api = _FakeTenantApi(organizations=[_org("org-1", name="Org One")], active_id="org-1")
    controller = _controller(api)
    controller.refresh()

    emitted = []
    controller.organizationSwitched.connect(lambda: emitted.append(1))

    assert controller.switchToOrganization("") is False
    assert emitted == []


def test_controller_with_no_api_degrades_gracefully():
    controller = _controller(None)

    controller.refresh()

    assert controller.organizations == []
    assert controller.activeOrganizationId == ""
    assert controller.isMultiOrganization is False
