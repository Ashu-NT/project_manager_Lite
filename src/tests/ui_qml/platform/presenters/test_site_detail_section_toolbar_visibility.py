"""Site Detail's outer per-section toolbar (title/subtitle/actions bar,
pinned below the header) is shown only for sections where it carries real
action buttons -- Overview (Refresh) and Calendar (assignment actions).
Activity's own embedded TableToolbar already has Refresh, so the outer bar
would otherwise render title/subtitle with zero buttons."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

DETAIL_PAGE = Path(
    "src/ui_qml/platform/qml/workspaces/sites/AdminSiteDetailPage.qml"
)

_SITE_PAYLOAD = {
    "id": "site-1",
    "title": "Test Site",
    "statusLabel": {"label": "Active", "tone": "success"},
    "subtitle": "SITE-1",
    "state": {"siteId": "site-1", "organizationId": "org-1", "isActive": True},
}


def _load(engine):
    load_qml(
        engine,
        DETAIL_PAGE.resolve(),
        initial_properties={"site": _SITE_PAYLOAD},
    )
    return engine.rootObjects()[0]


def test_outer_toolbar_shown_for_overview_and_calendar_only(qapp) -> None:
    engine = create_qml_engine()
    try:
        root = _load(engine)

        sections = root.property("_sections")
        sections = sections.toVariant() if hasattr(sections, "toVariant") else sections
        labels = [s["label"] for s in sections]
        assert labels == ["Overview", "Departments", "Employees", "Calendar", "Activity"]

        for index, label in enumerate(labels):
            root.setProperty("activeSectionIndex", index)
            shown = root.property("_showSectionToolbar")
            expected = label in ("Overview", "Calendar")
            assert shown == expected, f"{label}: expected _showSectionToolbar={expected}, got {shown}"
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
