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


def _organization_with_status(status: str, *, tone: str):
    org = _populated_organization()
    org["statusLabel"] = {"label": status.capitalize(), "tone": tone}
    org["state"]["status"] = status
    org["state"]["location"] = "New York, United States"
    return org


def _menu_ids(items):
    return [entry["id"] for entry in items if "id" in entry]


def test_active_organization_header_badge_and_actions_menu():
    _engine, root = _load_detail_page(_organization_with_status("active", tone="success"))

    assert root.property("_orgStatus") == "Active"
    assert root.property("_orgStatusTone") == "success"
    assert root.property("_headerSubtitle") == "ACME  ·  New York, United States"
    assert root.property("_showLifecycleMenu") is True

    items = root.property("_lifecycleMenuItems")
    items = items.toVariant() if hasattr(items, "toVariant") else items
    ids = _menu_ids(items)
    assert ids == ["edit", "deactivate", "archive"]
    assert items[1]["separator"] is True


def test_inactive_organization_actions_menu_offers_activate_not_deactivate():
    _engine, root = _load_detail_page(_organization_with_status("inactive", tone="neutral"))

    assert root.property("_showLifecycleMenu") is True
    items = root.property("_lifecycleMenuItems")
    items = items.toVariant() if hasattr(items, "toVariant") else items
    assert _menu_ids(items) == ["edit", "activate", "archive"]


def test_archived_organization_has_no_lifecycle_actions_in_the_menu():
    """Archived is terminal (OrganizationService._require_valid_organization_
    transition rejects every transition out of it) -- the Actions menu must
    not offer a reactivation/deactivation command that would only be
    rejected by the backend. The whole menu trigger is hidden rather than
    shown with nothing but a duplicate Edit in it."""
    _engine, root = _load_detail_page(_organization_with_status("archived", tone="neutral"))

    assert root.property("_orgStatus") == "Archived"
    assert root.property("_showLifecycleMenu") is False


def test_detail_page_loads_with_no_console_errors_for_every_lifecycle_status():
    """Loads the real QML file (not just reads its properties) for each of
    ACTIVE/INACTIVE/ARCHIVED and scans Qt's own message handler for
    ReferenceError/TypeError/unknown-icon-name -- the same technique that
    caught an undefined _joinNonEmpty() call during this phase's header
    rework, which a pure property-read assertion missed because QML just
    leaves a failed binding at its default value instead of raising."""
    from PySide6.QtCore import qInstallMessageHandler

    for status, tone in (("active", "success"), ("inactive", "neutral"), ("archived", "neutral")):
        messages: list[str] = []
        previous_handler = qInstallMessageHandler(lambda t, c, m: messages.append(str(m)))
        try:
            engine, root = _load_detail_page(_organization_with_status(status, tone=tone))
        finally:
            qInstallMessageHandler(previous_handler)

        relevant = [
            m for m in messages
            if "TypeError" in m or "ReferenceError" in m or "is not defined" in m
            or "unknown icon name" in m or "Cannot read propert" in m
        ]
        assert relevant == [], f"status={status!r}: {relevant}"
        engine.deleteLater()


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
