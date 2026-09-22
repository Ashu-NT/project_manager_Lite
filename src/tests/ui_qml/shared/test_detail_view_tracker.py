"""`App.Widgets.DetailViewTracker` -- the generic, module-agnostic signal a
shell watches to know "is *some* record's detail view open right now",
used to auto-collapse the global navigation sidebar. Every SectionDetailPage
instance (the shared detail-page shell used by Platform, Project
Management, and any future module) reports itself here on creation/
destruction; no per-workspace or per-module wiring is required."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

HARNESS = Path(__file__).with_name("_detail_view_tracker_harness.qml")


def _process_events(times: int = 15) -> None:
    for _ in range(times):
        QCoreApplication.processEvents()


def test_tracker_increments_on_open_and_decrements_on_close(qapp) -> None:
    engine = create_qml_engine()
    try:
        load_qml(engine, HARNESS.resolve(), initial_properties={})
        root = engine.rootObjects()[0]
        _process_events()

        assert root.property("trackerOpenCount") == 0
        assert root.property("trackerAnyOpen") is False

        root.setProperty("detailOpen", True)
        _process_events()
        assert root.property("trackerOpenCount") == 1
        assert root.property("trackerAnyOpen") is True

        root.setProperty("detailOpen", False)
        _process_events()
        assert root.property("trackerOpenCount") == 0
        assert root.property("trackerAnyOpen") is False
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        _process_events()


def test_tracker_stays_open_while_a_nested_detail_view_is_also_open(qapp) -> None:
    """Organization Detail's own Sites tab nests a second SectionDetailPage
    (AdminSiteDetailPage) when a site row is opened. The counter (not a
    plain boolean) must stay > 0 -- and anyOpen must stay True -- as long
    as EITHER level is still open; closing the inner one first must not
    make the shell think no detail view is open at all."""
    engine = create_qml_engine()
    try:
        load_qml(engine, HARNESS.resolve(), initial_properties={})
        root = engine.rootObjects()[0]
        _process_events()

        root.setProperty("detailOpen", True)
        _process_events()
        assert root.property("trackerOpenCount") == 1
        assert root.property("trackerAnyOpen") is True

        # A second SectionDetailPage-based page opens within the SAME
        # engine (simulating the nested Site Detail) while the first stays
        # open -- QML singletons are per-engine, so this must happen in the
        # same engine to share the real tracker instance.
        root.setProperty("nestedDetailOpen", True)
        _process_events()
        assert root.property("trackerOpenCount") == 2
        assert root.property("trackerAnyOpen") is True

        root.setProperty("nestedDetailOpen", False)
        _process_events()
        assert root.property("trackerOpenCount") == 1
        assert root.property("trackerAnyOpen") is True

        root.setProperty("detailOpen", False)
        _process_events()
        assert root.property("trackerOpenCount") == 0
        assert root.property("trackerAnyOpen") is False
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        _process_events()
