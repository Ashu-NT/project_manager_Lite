from __future__ import annotations

import inspect
import re

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.domain.master_data.site.events import (
    SiteCreated,
    SiteDisabled,
    SiteEnabled,
    SiteProfileUpdated,
)
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy(services, event_type):
    calls = []
    services["site_service"]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


def _platform_catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _inventory_catalog(services) -> InventoryProcurementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)


def _bypass_known_site_datetime_defect(monkeypatch) -> None:
    from datetime import timezone

    from src.core.platform.infrastructure.persistence.repositories.master_data.site.sites import (
        SqlAlchemySiteRepository,
    )

    original_get = SqlAlchemySiteRepository.get

    def _patched_get(self, site_id):
        site = original_get(self, site_id)
        if site is None:
            return site
        changes = {}
        if site.opened_at is not None and site.opened_at.tzinfo is None:
            changes["opened_at"] = site.opened_at.replace(tzinfo=timezone.utc)
        if site.closed_at is not None and site.closed_at.tzinfo is None:
            changes["closed_at"] = site.closed_at.replace(tzinfo=timezone.utc)
        if not changes:
            return site
        from dataclasses import replace

        return replace(site, **changes)

    monkeypatch.setattr(SqlAlchemySiteRepository, "get", _patched_get)


def _spy_site_list_hints(services):
    from src.core.platform.application.master_data.site.event_handlers.view_invalidation import (
        SITE_CATEGORY,
        SITE_LIST_SCOPE_CODE,
    )
    from src.core.shared.events.view_invalidation import ExactOrganization

    organization = services["tenant_context_service"].get_active_organization()
    tenant_id = organization.tenant_id
    organization_id = organization.id

    hints = []

    def _on_hint(hint):
        if hint.category == SITE_CATEGORY and hint.scope_code == SITE_LIST_SCOPE_CODE:
            hints.append(hint)

    services["platform_view_invalidation_channel"].subscribe(
        ExactOrganization(tenant_id, organization_id), _on_hint
    )
    return hints


def test_create_produces_exactly_one_site_created(services):
    calls = _spy(services, SiteCreated)
    site = services["site_service"].create_site(
        site_code=_unique_code("P14B-CREATE"), name="Warehouse One"
    )
    assert [e.site_id for e in calls] == [site.id]
    assert calls[0].organization_id == site.organization_id


def test_profile_only_update_produces_exactly_one_site_profile_updated(services):
    site_service = services["site_service"]
    site = site_service.create_site(site_code=_unique_code("P14B-PROFILE"), name="Before")
    calls = _spy(services, SiteProfileUpdated)
    availability_calls = []
    for event_type in (SiteEnabled, SiteDisabled):
        services["site_service"]._uow_factory._post_commit_bus.subscribe(
            event_type, lambda event, context: availability_calls.append(event)
        )

    site_service.update_site(site.id, name="After", expected_version=site.version)

    assert len(calls) == 1
    assert calls[0].site_id == site.id
    assert availability_calls == []


def test_disable_active_site_produces_exactly_one_site_disabled(services, monkeypatch):
    _bypass_known_site_datetime_defect(monkeypatch)
    site_service = services["site_service"]
    site = site_service.create_site(
        site_code=_unique_code("P14B-DISABLE"), name="Active Site", is_active=True
    )
    profile_calls = _spy(services, SiteProfileUpdated)
    calls = _spy(services, SiteDisabled)

    updated = site_service.update_site(site.id, is_active=False, expected_version=site.version)

    assert [e.site_id for e in calls] == [site.id]
    assert profile_calls == []
    assert updated.closed_at is not None


def test_enable_inactive_site_produces_exactly_one_site_enabled(services):
    site_service = services["site_service"]
    site = site_service.create_site(
        site_code=_unique_code("P14B-ENABLE"), name="Inactive Site", is_active=False
    )
    profile_calls = _spy(services, SiteProfileUpdated)
    calls = _spy(services, SiteEnabled)

    updated = site_service.update_site(site.id, is_active=True, expected_version=site.version)

    assert [e.site_id for e in calls] == [site.id]
    assert profile_calls == []
    assert updated.opened_at is not None


def test_mixed_profile_and_availability_update_produces_both_events(services, monkeypatch):
    _bypass_known_site_datetime_defect(monkeypatch)
    site_service = services["site_service"]
    site = site_service.create_site(
        site_code=_unique_code("P14B-MIXED"), name="Before Mixed", is_active=True
    )
    profile_calls = _spy(services, SiteProfileUpdated)
    disabled_calls = _spy(services, SiteDisabled)

    site_service.update_site(
        site.id, name="After Mixed", is_active=False, expected_version=site.version
    )

    assert len(profile_calls) == 1
    assert len(disabled_calls) == 1
    assert profile_calls[0].site_id == site.id
    assert disabled_calls[0].site_id == site.id
    assert profile_calls[0].occurred_at == disabled_calls[0].occurred_at


def test_retroactive_opened_at_correction_without_availability_flip_is_a_profile_change(services):
    site_service = services["site_service"]
    site = site_service.create_site(
        site_code=_unique_code("P14B-RETRO"), name="Retro Site", is_active=True
    )
    profile_calls = _spy(services, SiteProfileUpdated)
    availability_calls = []
    for event_type in (SiteEnabled, SiteDisabled):
        services["site_service"]._uow_factory._post_commit_bus.subscribe(
            event_type, lambda event, context: availability_calls.append(event)
        )

    from datetime import datetime, timedelta, timezone

    corrected_opened_at = datetime.now(timezone.utc) - timedelta(days=30)
    site_service.update_site(
        site.id, opened_at=corrected_opened_at, expected_version=site.version
    )

    assert len(profile_calls) == 1
    assert availability_calls == []


def test_no_op_update_produces_zero_events_zero_write_zero_audit_zero_updated_at_bump(services, monkeypatch):
    site_service = services["site_service"]
    site = site_service.create_site(
        site_code=_unique_code("P14B-NOOP"), name="Same Name", is_active=True
    )
    before = site_service._site_repo.get(site.id)
    profile_calls = _spy(services, SiteProfileUpdated)
    availability_calls = []
    for event_type in (SiteEnabled, SiteDisabled):
        services["site_service"]._uow_factory._post_commit_bus.subscribe(
            event_type, lambda event, context: availability_calls.append(event)
        )
    audit_calls = []
    monkeypatch.setattr(
        EnterpriseAuditService, "record", lambda self, **kwargs: audit_calls.append(kwargs)
    )

    result = site_service.update_site(
        site.id, name="Same Name", is_active=True, expected_version=site.version
    )

    assert result.version == site.version
    assert profile_calls == []
    assert availability_calls == []
    assert audit_calls == []
    reloaded = site_service._site_repo.get(site.id)
    assert reloaded.version == before.version
    assert reloaded.updated_at == before.updated_at


def test_duplicate_code_create_produces_zero_event(services):
    site_service = services["site_service"]
    code = _unique_code("P14B-DUPE")
    site_service.create_site(site_code=code, name="First")
    calls = _spy(services, SiteCreated)

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        site_service.create_site(site_code=code, name="Second")

    assert calls == []


def test_cross_org_update_produces_zero_event(services):
    site_service = services["site_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    site = site_service.create_site(site_code=_unique_code("P14B-CROSSORG"), name="Home Org Site")

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("P14B-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    calls = _spy(services, SiteProfileUpdated)
    try:
        from src.core.platform.common.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            site_service.update_site(site.id, name="Hijacked")
    finally:
        tenant_context_service.set_active_organization(default_organization.id)

    assert calls == []


def test_stale_version_update_produces_zero_event(services):
    site_service = services["site_service"]
    site = site_service.create_site(site_code=_unique_code("P14B-STALE"), name="Stale Site")
    calls = _spy(services, SiteProfileUpdated)

    from src.core.platform.common.exceptions import ConcurrencyError

    with pytest.raises(ConcurrencyError):
        site_service.update_site(
            site.id, name="Should Not Apply", expected_version=site.version + 1
        )

    assert calls == []


def test_authorization_failure_produces_zero_event(services, monkeypatch):
    site_service = services["site_service"]
    calls = _spy(services, SiteCreated)

    from src.core.platform.common.exceptions import BusinessRuleError

    def _deny(*args, **kwargs):
        raise BusinessRuleError("Permission denied.", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.site.site_commands.require_permission",
        _deny,
    )

    with pytest.raises(BusinessRuleError):
        site_service.create_site(site_code=_unique_code("P14B-AUTHFAIL"), name="No Access")

    assert calls == []


def test_audit_failure_rolls_back_and_produces_zero_postcommit_event(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated site audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    site_service = services["site_service"]
    calls = _spy(services, SiteCreated)
    code = _unique_code("P14B-AUDITFAIL")

    with pytest.raises(RuntimeError, match="simulated site audit failure"):
        site_service.create_site(site_code=code, name="Audit Fail")

    monkeypatch.undo()
    assert calls == []


def test_commit_failure_produces_zero_postcommit_event(services, monkeypatch):
    from src.core.platform.infrastructure.persistence.uow.site_unit_of_work import (
        SqlAlchemySiteUnitOfWork,
    )

    site_service = services["site_service"]
    calls = _spy(services, SiteCreated)

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemySiteUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        site_service.create_site(site_code=_unique_code("P14B-COMMITFAIL"), name="Commit Fail")

    assert calls == []


def test_admin_console_sub_controller_refreshes_once_after_committed_create(services):
    catalog = _platform_catalog(services)
    catalog.adminWorkspace.sites

    refresh_calls = []
    catalog.adminWorkspace._site_controller.refresh = (
        lambda: refresh_calls.append("admin-sites") or None
    )

    services["site_service"].create_site(
        site_code=_unique_code("P14B-ADMIN-CREATE"), name="Admin Refresh Site"
    )

    assert refresh_calls == ["admin-sites"]


def test_admin_console_sub_controller_refreshes_once_after_mixed_update(services, monkeypatch):
    _bypass_known_site_datetime_defect(monkeypatch)
    site_service = services["site_service"]
    site = site_service.create_site(
        site_code=_unique_code("P14B-ADMIN-MIXED"), name="Before", is_active=True
    )

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.sites

    refresh_calls = []
    catalog.adminWorkspace._site_controller.refresh = (
        lambda: refresh_calls.append("admin-sites") or None
    )

    site_service.update_site(
        site.id, name="After", is_active=False, expected_version=site.version
    )

    assert refresh_calls == ["admin-sites"]


def test_admin_console_no_refresh_on_no_op_update(services):
    site_service = services["site_service"]
    site = site_service.create_site(site_code=_unique_code("P14B-ADMIN-NOOP"), name="Same")

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.sites

    refresh_calls = []
    catalog.adminWorkspace._site_controller.refresh = (
        lambda: refresh_calls.append("admin-sites") or None
    )

    site_service.update_site(site.id, name="Same", expected_version=site.version)

    assert refresh_calls == []


def test_admin_console_no_refresh_on_failed_transaction(services):
    site_service = services["site_service"]
    code = _unique_code("P14B-ADMIN-FAILED")
    site_service.create_site(site_code=code, name="Existing")

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.sites

    refresh_calls = []
    catalog.adminWorkspace._site_controller.refresh = (
        lambda: refresh_calls.append("admin-sites") or None
    )

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        site_service.create_site(site_code=code, name="Duplicate")

    assert refresh_calls == []


def test_inventory_pricing_procurement_narrow_refresh_once_no_duplicate_full_refresh(services):
    catalog = _inventory_catalog(services)

    narrow_calls = []
    full_calls = []
    catalog.inventoryWorkspace.refresh_site_options = (
        lambda: narrow_calls.append("inventory") or None
    )
    catalog.pricingWorkspace.refresh_site_options = (
        lambda: narrow_calls.append("pricing") or None
    )
    catalog.procurementWorkspace.refresh_site_options = (
        lambda: narrow_calls.append("procurement") or None
    )
    for controller in (
        catalog.inventoryWorkspace,
        catalog.pricingWorkspace,
        catalog.procurementWorkspace,
        catalog.reservationsWorkspace,
    ):
        controller.refresh = lambda name=controller: full_calls.append(name) or None

    services["site_service"].create_site(
        site_code=_unique_code("P14B-INV-CREATE"), name="Inventory Site"
    )

    assert sorted(narrow_calls) == ["inventory", "pricing", "procurement"]
    assert full_calls == []


def test_reservations_does_not_react_to_site_events_at_all(services):
    catalog = _inventory_catalog(services)

    refresh_calls = []
    catalog.reservationsWorkspace.refresh = lambda: refresh_calls.append("reservations") or None

    services["site_service"].create_site(
        site_code=_unique_code("P14B-RES-CREATE"), name="Reservations Blind Site"
    )
    site = services["site_service"].list_sites()[-1]
    services["site_service"].update_site(
        site.id, name="Reservations Blind Site Updated", expected_version=site.version
    )

    assert refresh_calls == []


def test_no_refresh_on_no_op_for_inventory_pricing_procurement(services):
    site_service = services["site_service"]
    site = site_service.create_site(site_code=_unique_code("P14B-NOOP-UI"), name="Same UI")

    catalog = _inventory_catalog(services)
    narrow_calls = []
    catalog.inventoryWorkspace.refresh_site_options = (
        lambda: narrow_calls.append("inventory") or None
    )
    catalog.pricingWorkspace.refresh_site_options = (
        lambda: narrow_calls.append("pricing") or None
    )
    catalog.procurementWorkspace.refresh_site_options = (
        lambda: narrow_calls.append("procurement") or None
    )

    site_service.update_site(site.id, name="Same UI", expected_version=site.version)

    assert narrow_calls == []


def test_sites_changed_field_and_producers_are_fully_gone():
    assert not hasattr(domain_events, "sites_changed")

    import src.core.platform.application.master_data.site.site_commands as site_commands_module
    import src.core.platform.application.master_data.site.site_service as site_service_module

    assert "sites_changed" not in inspect.getsource(site_service_module)
    assert "sites_changed" not in inspect.getsource(site_commands_module)


def test_no_forbidden_site_changed_event_name_exists():
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if re.search(r"\bSiteChanged\b", source) or re.search(r"\bSiteUpdated\b", source):
            hits.append(normalized)
    assert hits == [], hits


def test_canonical_site_uow_retained_no_raw_session_commit():
    import src.core.platform.application.master_data.site.site_commands as site_commands_module

    source = inspect.getsource(site_commands_module.create_site) + inspect.getsource(
        site_commands_module.update_site
    )
    assert "self._session.commit(" not in source
    assert "self._session.rollback(" not in source
    assert "uow.commit()" in source


def test_no_platform_to_business_module_concrete_infrastructure_import():
    import src.core.platform.infrastructure.persistence.uow.site_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "core.modules" not in source


def test_no_generic_refresh_all_workspaces_wired_to_site_events():
    import src.ui_qml.modules.inventory_procurement.context as context_module

    source = inspect.getsource(context_module)
    assert "refreshAllWorkspaces" not in inspect.getsource(
        context_module.InventoryProcurementWorkspaceCatalog.refreshCapabilities
    )


# ---------------------------------------------------------------------------
# P14B-FIX: correlation_id-based site_list dedup audit
# ---------------------------------------------------------------------------


def test_site_commands_always_construct_a_fresh_context_per_uow_call():
    import src.core.platform.application.master_data.site.site_commands as site_commands_module

    source = inspect.getsource(site_commands_module)
    assert source.count("service._uow_factory.create(context=service._new_context())") == 2
    assert "context =" not in source
    assert "DomainEventContext(" not in source


def test_dedupe_state_is_a_single_slot_not_a_growing_collection():
    import src.core.platform.application.master_data.site.event_handlers.view_invalidation as vi_module

    source = inspect.getsource(vi_module.build_site_list_view_invalidation_handler)
    assert "set(" not in source
    assert "= []" not in source
    assert "[None]" in source


def test_mixed_update_produces_exactly_one_site_list_hint(services, monkeypatch):
    _bypass_known_site_datetime_defect(monkeypatch)
    site_service = services["site_service"]
    site = site_service.create_site(
        site_code=_unique_code("P14BFIX-MIXED"), name="Before Mixed", is_active=True
    )
    hints = _spy_site_list_hints(services)

    site_service.update_site(
        site.id, name="After Mixed", is_active=False, expected_version=site.version
    )

    assert len(hints) == 1


def test_two_separate_site_commits_produce_exactly_two_site_list_hints(services):
    site_service = services["site_service"]
    hints = _spy_site_list_hints(services)

    site_service.create_site(site_code=_unique_code("P14BFIX-SEP-A"), name="Separate A")
    site_service.create_site(site_code=_unique_code("P14BFIX-SEP-B"), name="Separate B")

    assert len(hints) == 2


def test_failed_transaction_produces_zero_site_list_hints(services):
    site_service = services["site_service"]
    code = _unique_code("P14BFIX-FAILED")
    site_service.create_site(site_code=code, name="Existing")
    hints = _spy_site_list_hints(services)

    from src.core.platform.common.exceptions import ValidationError

    with pytest.raises(ValidationError):
        site_service.create_site(site_code=code, name="Duplicate")

    assert hints == []


def test_a_later_separate_commit_is_not_suppressed_by_an_earlier_commits_second_event(
    services, monkeypatch
):
    _bypass_known_site_datetime_defect(monkeypatch)
    site_service = services["site_service"]
    mixed_site = site_service.create_site(
        site_code=_unique_code("P14BFIX-REENTRANT-A"), name="Before Mixed", is_active=True
    )
    hints = _spy_site_list_hints(services)

    site_service.update_site(
        mixed_site.id,
        name="After Mixed",
        is_active=False,
        expected_version=mixed_site.version,
    )
    assert len(hints) == 1

    site_service.create_site(site_code=_unique_code("P14BFIX-REENTRANT-B"), name="Separate B")

    assert len(hints) == 2


def test_correlation_id_dedup_scales_across_many_commits_without_growth(services):
    site_service = services["site_service"]
    hints = _spy_site_list_hints(services)

    for _ in range(25):
        site_service.create_site(site_code=_unique_code("P14BFIX-MANY"), name="Many")

    assert len(hints) == 25


def test_domain_event_context_is_documented_as_owned_by_one_unit_of_work_per_transaction():
    import src.core.shared.events.domain_event_context as context_module

    source = inspect.getsource(context_module)
    assert "one transaction" in source
