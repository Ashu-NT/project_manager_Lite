from __future__ import annotations

import pytest

from src.core.platform.application.master_data.department.dto import (
    DepartmentCreateCommand,
)
from src.core.platform.application.master_data.party.dto import (
    PartyCreateCommand,
)
from src.core.platform.application.master_data.site.dto import (
    SiteCreateCommand,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.tests.ui_runtime_helpers import login_as


def test_resource_manager_can_query_shared_sites_and_departments_without_settings_manage(services):
    site = services["site_commands"].create_site(SiteCreateCommand(site_code="BER", name="Berlin Plant", city="Berlin"))
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="OPS", name="Operations", site_id=site.id, department_type="OPERATIONS"))
    services["user_registration"].register_user("resource-shared-reader", "StrongPass123", role_names=["resource_manager"])

    login_as(services, "resource-shared-reader", "StrongPass123")

    sites = services["site_query"].search_sites(search_text="ber", active_only=True)
    departments = services["department_query"].search_departments(search_text="ops", active_only=True)

    assert [row.id for row in services["site_query"].list_sites(active_only=True)] == [site.id]
    assert [row.id for row in sites] == [site.id]
    assert services["site_query"].find_site_by_code("BER").id == site.id
    assert services["site_query"].get_site(site.id).name == "Berlin Plant"

    assert [row.id for row in services["department_query"].list_departments(active_only=True)] == [department.id]
    assert [row.id for row in departments] == [department.id]
    assert services["department_query"].find_department_by_code("OPS").id == department.id
    assert services["department_query"].get_department(department.id).name == "Operations"


def test_finance_controller_can_query_shared_parties_without_settings_manage(services):
    party = services["party_commands"].create_party(PartyCreateCommand(party_code="SUP-001", party_name="North Supply", roles=["SUPPLIER"], city="Hamburg"))
    services["user_registration"].register_user("finance-party-reader", "StrongPass123", role_names=["finance_controller"])

    login_as(services, "finance-party-reader", "StrongPass123")

    parties = services["party_query"].search_parties(search_text="north", active_only=True)

    assert [row.id for row in services["party_query"].list_parties(active_only=True)] == [party.id]
    assert [row.id for row in parties] == [party.id]
    assert services["party_query"].find_party_by_code("SUP-001").id == party.id
    assert services["party_query"].get_party(party.id).party_name == "North Supply"


def test_viewer_cannot_read_shared_sites_departments_or_parties(services):
    services["site_commands"].create_site(SiteCreateCommand(site_code="BER", name="Berlin Plant"))
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="OPS", name="Operations"))
    services["party_commands"].create_party(PartyCreateCommand(party_code="SUP-001", party_name="North Supply"))
    services["user_registration"].register_user("shared-master-viewer", "StrongPass123", role_names=["viewer"])

    login_as(services, "shared-master-viewer", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="site.read"):
        services["site_query"].list_sites(active_only=True)
    with pytest.raises(BusinessRuleError, match="department.read"):
        services["department_query"].list_departments(active_only=True)
    with pytest.raises(BusinessRuleError, match="party.read"):
        services["party_query"].list_parties(active_only=True)

