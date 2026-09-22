"""AdminOrganizationDetailPage.qml -- Basic Information / Registered Address
/ Contact Information field grouping and the blank-value "-" placeholder
rule (never a bare empty string, "None", or "null")."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QGuiApplication

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

DETAIL_PAGE = Path(
    "src/ui_qml/platform/qml/workspaces/organizations/AdminOrganizationDetailPage.qml"
)

_QAPP: QGuiApplication | None = None


def _ensure_qgui_application() -> QGuiApplication:
    global _QAPP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    existing = QGuiApplication.instance()
    if existing is not None:
        _QAPP = existing
        return existing
    _QAPP = QGuiApplication(["org-detail-qml-test"])
    return _QAPP


def _load_detail_page(organization: dict):
    _ensure_qgui_application()
    engine = create_qml_engine()
    load_qml(
        engine,
        DETAIL_PAGE.resolve(),
        initial_properties={"organization": organization},
    )
    root = engine.rootObjects()[0]
    return engine, root


def _by_label(fields, label):
    for entry in fields:
        if entry.get("label") == label:
            return entry.get("value")
    raise AssertionError(f"field {label!r} not found in {fields!r}")


def _populated_organization():
    return {
        "id": "org-1",
        "title": "Acme Corp",
        "statusLabel": "Active",
        "subtitle": "ACME | UTC",
        "state": {
            "organizationCode": "ACME",
            "displayName": "Acme Corp",
            "timezoneName": "UTC",
            "baseCurrency": "USD",
            "status": "active",
            "legalName": "Acme Corp Holdings",
            "registrationNumber": "12345678",
            "taxId": "US-TAX-1",
            "addressLine1": "1 Main St",
            "addressLine2": "Suite 2",
            "postalCode": "10001",
            "city": "New York",
            "stateRegion": "NY",
            "countryCode": "US",
            "email": "contact@acme.example",
            "phone": "+1 555 0000",
            "website": "https://acme.example",
        },
    }


def _blank_organization():
    org = _populated_organization()
    for key in (
        "organizationCode", "timezoneName", "baseCurrency",
        "legalName", "registrationNumber", "taxId", "addressLine1", "addressLine2",
        "postalCode", "city", "stateRegion", "countryCode", "email", "phone", "website",
    ):
        org["state"][key] = ""
    return org


def test_populated_fields_render_real_values():
    _engine, root = _load_detail_page(_populated_organization())

    basic_info = root.property("_basicInfoFields")
    address = root.property("_addressFields")
    contact = root.property("_contactFields")
    basic_info = basic_info.toVariant() if hasattr(basic_info, "toVariant") else basic_info
    address = address.toVariant() if hasattr(address, "toVariant") else address
    contact = contact.toVariant() if hasattr(contact, "toVariant") else contact

    assert _by_label(basic_info, "Legal Name") == "Acme Corp Holdings"
    assert _by_label(basic_info, "Registration Number") == "12345678"
    assert _by_label(basic_info, "Tax / VAT ID") == "US-TAX-1"
    assert _by_label(address, "Address Line 1") == "1 Main St"
    assert _by_label(address, "City") == "New York"
    assert _by_label(contact, "Email") == "contact@acme.example"
    assert _by_label(contact, "Website") == "https://acme.example"


def test_blank_fields_render_the_placeholder_not_empty_or_none():
    _engine, root = _load_detail_page(_blank_organization())

    basic_info = root.property("_basicInfoFields")
    address = root.property("_addressFields")
    contact = root.property("_contactFields")
    basic_info = basic_info.toVariant() if hasattr(basic_info, "toVariant") else basic_info
    address = address.toVariant() if hasattr(address, "toVariant") else address
    contact = contact.toVariant() if hasattr(contact, "toVariant") else contact

    for entry in list(basic_info) + list(address) + list(contact):
        if entry["label"] in ("Status", "Organization Name"):
            # Status falls back to "Unknown"; Organization Name falls back to
            # the always-populated catalog title -- neither is ever truly blank.
            continue
        value = entry["value"]
        assert value == "—", f"{entry['label']!r} rendered {value!r}, expected the placeholder"
        assert value != ""
        assert value.lower() != "none"
        assert value.lower() != "null"
