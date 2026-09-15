"""Organization presenter -- legal/address/contact fields surfaced in the
serialized catalog row `state` (consumed by both the Inspector and Organization
Detail Overview), and the country reference options for the registered-address
picker."""

from __future__ import annotations

from types import SimpleNamespace

from src.ui_qml.platform.presenters.organizations.organization_catalog_presenter import (
    PlatformOrganizationCatalogPresenter,
)


def _organization_row(**overrides):
    base = dict(
        id="org-1",
        organization_code="ACME",
        display_name="Acme Corp",
        timezone_name="UTC",
        base_currency="USD",
        is_enabled=True,
        version=1,
        legal_name="Acme Corp Holdings",
        registration_number="12345678",
        tax_id="US-TAX-1",
        address_line_1="1 Main St",
        address_line_2="Suite 2",
        postal_code="10001",
        city="New York",
        state_region="NY",
        country_code="US",
        email="contact@acme.example",
        phone="+1 555 0000",
        website="https://acme.example",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeRuntimeApi:
    def __init__(self, rows, *, countries=()):
        self._rows = rows
        self._countries = countries

    def list_organizations_page(self, *, page=1, page_size=25, search=None, enabled_only=None):
        return SimpleNamespace(
            ok=True,
            data=SimpleNamespace(
                items=self._rows,
                total=len(self._rows),
                filtered_total=len(self._rows),
                page=page,
                page_size=page_size,
            ),
        )

    def list_countries(self):
        return SimpleNamespace(ok=True, data=self._countries)


def test_serialized_organization_state_carries_the_new_fields():
    presenter = PlatformOrganizationCatalogPresenter(
        runtime_api=_FakeRuntimeApi([_organization_row()])
    )
    catalog = presenter.build_catalog_page()
    state = catalog.items[0].state

    assert state["legalName"] == "Acme Corp Holdings"
    assert state["registrationNumber"] == "12345678"
    assert state["taxId"] == "US-TAX-1"
    assert state["addressLine1"] == "1 Main St"
    assert state["addressLine2"] == "Suite 2"
    assert state["postalCode"] == "10001"
    assert state["city"] == "New York"
    assert state["stateRegion"] == "NY"
    assert state["countryCode"] == "US"
    assert state["email"] == "contact@acme.example"
    assert state["phone"] == "+1 555 0000"
    assert state["website"] == "https://acme.example"


def test_serialized_organization_state_carries_blank_new_fields():
    presenter = PlatformOrganizationCatalogPresenter(
        runtime_api=_FakeRuntimeApi(
            [
                _organization_row(
                    legal_name="",
                    registration_number="",
                    tax_id="",
                    address_line_1="",
                    address_line_2="",
                    postal_code="",
                    city="",
                    state_region="",
                    country_code="",
                    email="",
                    phone="",
                    website="",
                )
            ]
        )
    )
    catalog = presenter.build_catalog_page()
    state = catalog.items[0].state

    assert state["legalName"] == ""
    assert state["email"] == ""
    assert state["countryCode"] == ""


def test_build_country_options_maps_code_and_name():
    countries = (
        SimpleNamespace(code="US", name="United States of America"),
        SimpleNamespace(code="NL", name="Netherlands"),
    )
    presenter = PlatformOrganizationCatalogPresenter(
        runtime_api=_FakeRuntimeApi([], countries=countries)
    )
    options = presenter.build_country_options()

    assert options == (
        {"label": "United States of America", "value": "US", "supportingText": ""},
        {"label": "Netherlands", "value": "NL", "supportingText": ""},
    )


def test_build_country_options_handles_missing_runtime_api():
    presenter = PlatformOrganizationCatalogPresenter(runtime_api=None)
    assert presenter.build_country_options() == ()
