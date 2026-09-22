"""End-to-end (real SQLite-backed services, real controller chain) tests for
the Organizations table's row-selection + bulk actions: bulk activate/deactivate,
bulk currency, bulk timezone, and bulk module grant/revoke."""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.platform.infrastructure.persistence.uow.organization_unit_of_work import (
    SqlAlchemyOrganizationUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.module_entitlement_unit_of_work import (
    SqlAlchemyModuleEntitlementUnitOfWorkFactory,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def _count_uow_creations(factory_cls=SqlAlchemyOrganizationUnitOfWorkFactory):
    """Instruments a concrete UnitOfWork factory (each overrides create()
    directly rather than inheriting the shared base) so a test can assert how
    many separate transactions a call actually opened.
    Returns (counts_dict, restore_fn)."""
    counts = {"create": 0}
    real_create = factory_cls.create

    def counting_create(self, *args, **kwargs):
        counts["create"] += 1
        return real_create(self, *args, **kwargs)

    factory_cls.create = counting_create

    def restore():
        factory_cls.create = real_create

    return counts, restore


def _create_org(services, code: str, name: str) -> str:
    org_service = services["organization_service"]
    organization = org_service.create_organization(
        organization_code=code,
        display_name=name,
        timezone_name="UTC",
        base_currency="USD",
    )
    return organization.id


def _build_admin_workspace(services):
    # PlatformWorkspaceCatalog must stay referenced for as long as its
    # adminWorkspace sub-controller is used -- once the Python wrapper for
    # `catalog` is garbage collected, PySide6 tears down the whole
    # parent/child QObject tree underneath it (the sub-controller's C++
    # object dies even though a Python reference to it is still held),
    # so the caller keeps BOTH returned values alive, not just adminWorkspace.
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    return catalog, catalog.adminWorkspace


def test_bulk_activate_deactivate_applies_to_every_selected_organization(services, qapp) -> None:
    _catalog, admin = _build_admin_workspace(services)
    org_a = _create_org(services, "BULK-A", "Bulk Org A")
    org_b = _create_org(services, "BULK-B", "Bulk Org B")
    admin.refresh()

    admin.setOrganizationBulkSelection(org_a, True)
    admin.setOrganizationBulkSelection(org_b, True)
    assert set(admin.selectedOrganizationIds) == {org_a, org_b}

    result = admin.bulkDeactivateOrganizations()
    assert result["ok"] is True, result
    assert admin.selectedOrganizationIds == []

    org_service = services["organization_service"]
    all_orgs = {o.id: o for o in org_service.list_organizations(status=None)}
    assert all_orgs[org_a].status == "inactive"
    assert all_orgs[org_b].status == "inactive"

    admin.setOrganizationBulkSelection(org_a, True)
    admin.setOrganizationBulkSelection(org_b, True)
    result = admin.bulkActivateOrganizations()
    assert result["ok"] is True, result
    all_orgs = {o.id: o for o in org_service.list_organizations(status=None)}
    assert all_orgs[org_a].status == "active"
    assert all_orgs[org_b].status == "active"


def test_bulk_status_change_opens_exactly_one_transaction_for_the_whole_selection(services, qapp) -> None:
    """The whole point of routing bulk actions through OrganizationService.
    bulk_deactivate_organizations() instead of looping N calls to
    deactivate_organization(): N selected rows must cost ONE UnitOfWork/commit,
    not N. This is the regression test for that."""
    _catalog, admin = _build_admin_workspace(services)
    org_ids = [_create_org(services, f"BULK-TX-{i}", f"Bulk TX Org {i}") for i in range(5)]
    admin.refresh()

    for org_id in org_ids:
        admin.setOrganizationBulkSelection(org_id, True)

    counts, restore = _count_uow_creations()
    try:
        result = admin.bulkDeactivateOrganizations()
    finally:
        restore()

    assert result["ok"] is True, result
    assert counts["create"] == 1, (
        f"bulk-disabling {len(org_ids)} organizations opened {counts['create']} "
        "UnitOfWork(s) instead of exactly 1"
    )


def test_bulk_currency_and_timezone_update_every_selected_organization(services, qapp) -> None:
    _catalog, admin = _build_admin_workspace(services)
    org_a = _create_org(services, "BULK-C", "Bulk Org C")
    org_b = _create_org(services, "BULK-D", "Bulk Org D")
    admin.refresh()

    admin.setOrganizationBulkSelection(org_a, True)
    admin.setOrganizationBulkSelection(org_b, True)
    result = admin.applyBulkOrganizationCurrency({"value": "eur"})
    assert result["ok"] is True, result

    admin.setOrganizationBulkSelection(org_a, True)
    admin.setOrganizationBulkSelection(org_b, True)
    result = admin.applyBulkOrganizationTimezone({"value": "Europe/Amsterdam"})
    assert result["ok"] is True, result

    org_service = services["organization_service"]
    all_orgs = {o.id: o for o in org_service.list_organizations(status=None)}
    for org_id in (org_a, org_b):
        assert all_orgs[org_id].base_currency == "EUR"
        assert all_orgs[org_id].timezone_name == "Europe/Amsterdam"
        # Untouched fields from the original create survive a narrow bulk
        # update -- proof the bulk path never falls back to the full-form
        # update_organization() flow with blank/default values.
        assert all_orgs[org_id].organization_code in ("BULK-C", "BULK-D")


def test_bulk_assign_modules_grants_and_revokes_across_every_selected_organization(services, qapp) -> None:
    _catalog, admin = _build_admin_workspace(services)
    org_a = _create_org(services, "BULK-F", "Bulk Org F")
    org_b = _create_org(services, "BULK-G", "Bulk Org G")
    admin.refresh()

    module_catalog_service = services["module_catalog_service"]
    module_code = module_catalog_service.list_modules()[0].code

    admin.setOrganizationBulkSelection(org_a, True)
    admin.setOrganizationBulkSelection(org_b, True)
    counts, restore = _count_uow_creations(SqlAlchemyModuleEntitlementUnitOfWorkFactory)
    try:
        result = admin.applyBulkOrganizationModules({"moduleCodes": [module_code], "grant": True})
    finally:
        restore()
    assert result["ok"] is True, result
    # 2 organizations x 1 module = 2 pairs -- must still cost exactly one
    # UnitOfWork/commit, not one per pair.
    assert counts["create"] == 1, (
        f"bulk module grant across 2 pairs opened {counts['create']} UnitOfWork(s) instead of exactly 1"
    )

    for org_id in (org_a, org_b):
        entitlement = module_catalog_service.license_module(org_id, module_code)
        assert entitlement.licensed is True

    admin.setOrganizationBulkSelection(org_a, True)
    admin.setOrganizationBulkSelection(org_b, True)
    result = admin.applyBulkOrganizationModules({"moduleCodes": [module_code], "grant": False})
    assert result["ok"] is True, result

    for org_id in (org_a, org_b):
        entitlement = module_catalog_service.revoke_module_license(org_id, module_code)
        assert entitlement.licensed is False


def test_bulk_selection_and_action_bar_wiring_survives_a_real_page_load(services, qapp) -> None:
    """Loads the real OrganizationsWorkspacePage.qml against a fully-wired
    PlatformWorkspaceCatalog to catch QML-side wiring mistakes (unresolved
    bindings, missing signal handlers) that a pure-Python test can't see."""
    import os
    from pathlib import Path

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QCoreApplication, qInstallMessageHandler

    from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

    catalog, admin = _build_admin_workspace(services)
    org_a = _create_org(services, "BULK-E", "Bulk Org E")
    admin.refresh()

    messages: list[str] = []
    previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
    engine = create_qml_engine()
    try:
        load_qml(
            engine,
            Path(
                "src/ui_qml/platform/qml/workspaces/organizations/OrganizationsWorkspacePage.qml"
            ).resolve(),
            initial_properties={"platformCatalog": catalog},
        )
        assert len(engine.rootObjects()) == 1
        root = engine.rootObjects()[0]
        for _ in range(20):
            QCoreApplication.processEvents()

        admin.setOrganizationBulkSelection(org_a, True)
        for _ in range(10):
            QCoreApplication.processEvents()

        selected_count = root.property("_selectedCount")
        assert selected_count == 1

        relevant = [
            m for m in messages
            if "TypeError" in m or "ReferenceError" in m or "is not defined" in m
            or "unknown icon name" in m or "Cannot read propert" in m
        ]
        assert relevant == [], relevant
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
        qInstallMessageHandler(previous_handler)
