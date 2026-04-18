from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from tests.ui_runtime_helpers import login_as


def test_resource_manager_can_query_shared_sites_and_departments_without_settings_manage(services):
    auth = services["auth_service"]
    site = services["site_service"].create_site(site_code="BER", name="Berlin Plant", city="Berlin")
    department = services["department_service"].create_department(
        department_code="OPS",
        name="Operations",
        site_id=site.id,
        department_type="OPERATIONS",
    )
    auth.register_user("resource-shared-reader", "StrongPass123", role_names=["resource_manager"])

    login_as(services, "resource-shared-reader", "StrongPass123")

    sites = services["site_service"].search_sites(search_text="ber", active_only=True)
    departments = services["department_service"].search_departments(search_text="ops", active_only=True)

    assert [row.id for row in services["site_service"].list_sites(active_only=True)] == [site.id]
    assert [row.id for row in sites] == [site.id]
    assert services["site_service"].find_site_by_code("BER").id == site.id
    assert services["site_service"].get_site(site.id).name == "Berlin Plant"

    assert [row.id for row in services["department_service"].list_departments(active_only=True)] == [department.id]
    assert [row.id for row in departments] == [department.id]
    assert services["department_service"].find_department_by_code("OPS").id == department.id
    assert services["department_service"].get_department(department.id).name == "Operations"


def test_finance_controller_can_query_shared_parties_without_settings_manage(services):
    auth = services["auth_service"]
    party = services["party_service"].create_party(
        party_code="SUP-001",
        party_name="North Supply",
        party_type="SUPPLIER",
        city="Hamburg",
    )
    auth.register_user("finance-party-reader", "StrongPass123", role_names=["finance_controller"])

    login_as(services, "finance-party-reader", "StrongPass123")

    parties = services["party_service"].search_parties(search_text="north", active_only=True)

    assert [row.id for row in services["party_service"].list_parties(active_only=True)] == [party.id]
    assert [row.id for row in parties] == [party.id]
    assert services["party_service"].find_party_by_code("SUP-001").id == party.id
    assert services["party_service"].get_party(party.id).party_name == "North Supply"


def test_viewer_cannot_read_shared_sites_departments_or_parties(services):
    auth = services["auth_service"]
    services["site_service"].create_site(site_code="BER", name="Berlin Plant")
    services["department_service"].create_department(department_code="OPS", name="Operations")
    services["party_service"].create_party(party_code="SUP-001", party_name="North Supply")
    auth.register_user("shared-master-viewer", "StrongPass123", role_names=["viewer"])

    login_as(services, "shared-master-viewer", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="site.read"):
        services["site_service"].list_sites(active_only=True)
    with pytest.raises(BusinessRuleError, match="department.read"):
        services["department_service"].list_departments(active_only=True)
    with pytest.raises(BusinessRuleError, match="party.read"):
        services["party_service"].list_parties(active_only=True)
