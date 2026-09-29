"""Shared-component regression: `SectionDetailPage`'s pinned-content region
(`stickyHost`/`stickyColumn`) used to be a plain `Column` positioner, with
`stickyHost` itself gated `visible: implicitHeight > 0`. `_syncPinnedContent()`
reparents `detailPagePinned: true` children into it imperatively (via
`Qt.callLater`), outside normal declarative QML construction. Three
compounding failure modes were found (all reproduced live against a real
running Site Detail page, not just reasoned about):

1. A `Column`/`Row`/`Grid` positioner does not reliably track a later-
   reparented child's visibility/geometry changes at all, so once such a
   child's `visible` binding flipped AFTER the reparent (e.g. switching
   detail page tabs), the positioner's bookkeeping and the item's own
   effective visibility silently fell out of sync and `stickyHost`
   permanently collapsed to zero height.
2. Switching `stickyColumn` to a `ColumnLayout` fixes the *first* render,
   but a `Layout` goes further: it can actively re-assert `visible: false`
   on a reparented child during its own relayout pass when the child's
   `implicitWidth` reads 0 (true for a bare Rectangle/Item that only sets
   an explicit `width` override, since Layouts size from `implicitWidth`/
   `Layout.preferredWidth`, never the literal `width` property) -- this
   overrode even a direct `setProperty("visible", True)`, which read back
   `False` on the very next event-loop tick.
3. Even after avoiding both (1) and (2) with a plain, manually-positioned
   `Item`, `stickyHost` being `visible: implicitHeight > 0` -- i.e.
   explicitly invisible whenever empty -- silently suppressed *descendant*
   visibility-binding evaluation while it was invisible: a pinned child's
   `visible` binding stopped tracking its source property and read back
   stale/false even long after the source flipped true again and
   stickyHost had become visible once more. This is why the round-trip
   (hide -> show again) stayed broken even after fixing (1) and (2) --
   `stickyHost` must never itself be `visible: false`; `implicitHeight: 0`
   (plus `clip: true`, so empty content never visually leaks) already
   makes it take no space.

All three are avoided by never handing size/visibility authority to any
automatic container: `stickyColumn` is a plain `Item`, `stickyHost` is
never explicitly hidden, and `_relayoutStickyColumn()` positions and sizes
every pinned child explicitly (stacked top-to-bottom, skipping invisible
ones), driving `stickyHost`'s height itself.

This test reproduces the failure shape at the shared-component level (not a
Site- or Organization-specific test) by loading a minimal probe QML file
that wraps `SectionDetailPage` with a synthetic pinned child and toggling
its visibility through a full show -> hide -> show round trip (the second
"show" is exactly the transition failure mode 3 broke), using the same
`create_qml_engine`/`load_qml` bootstrap the real app and its other QML
regression tests use (a bare `QQmlComponent.create()` + `setProperty()`
does not faithfully reproduce this -- `load_qml`'s `setInitialProperties`
sets properties before `Component.onCompleted` fires, which matters here
since `_syncPinnedContent` is scheduled from `Component.onCompleted` via
`Qt.callLater`)."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication
from PySide6.QtQuick import QQuickItem

from src.ui_qml.shell.qml_engine import create_qml_engine, load_qml

_PROBE_QML = """
import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets

Window {
    id: win
    objectName: "probeWindow"
    width: 900
    height: 600
    visible: true

    property alias toolbarShown: page.toolbarShown

    AppWidgets.SectionDetailPage {
        id: page
        objectName: "probePage"
        anchors.fill: parent
        open: true
        title: "Probe"
        sections: [{"label": "Overview"}, {"label": "Other"}]

        property bool toolbarShown: true

        Rectangle {
            id: pinnedToolbar
            objectName: "pinnedToolbar"
            property bool detailPagePinned: true
            visible: page.toolbarShown
            height: visible ? implicitHeight : 0
            width: parent ? parent.width : page.width
            implicitHeight: 42
            color: "red"
        }

        Rectangle {
            objectName: "unpinnedContent"
            width: 100
            height: 300
            color: "blue"
        }
    }
}
"""


def _settle(app, *, seconds: float = 1.0) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)


def test_pinned_toolbar_visibility_and_width_survive_section_switches(qapp) -> None:
    qml_path = Path(tempfile.mktemp(suffix=".qml"))
    qml_path.write_text(_PROBE_QML, encoding="utf-8")

    engine = create_qml_engine()
    try:
        load_qml(engine, qml_path)
        assert engine.rootObjects(), "probe QML failed to load"
        root = engine.rootObjects()[0]
        _settle(qapp)

        toolbar = root.findChild(QQuickItem, "pinnedToolbar")
        assert toolbar is not None
        assert toolbar.parentItem() is not None
        assert toolbar.parentItem().objectName() == "stickyColumn", (
            "pinned child was not reparented into stickyColumn -- "
            f"parent objectName is {toolbar.parentItem().objectName()!r}"
        )

        # Shown: must have real height AND real width.
        assert toolbar.property("visible") is True
        assert toolbar.height() > 0
        assert toolbar.width() > 0, (
            "pinned child has zero width -- Layout.fillWidth is not taking "
            "effect, meaning the sticky container is not a real Layout"
        )

        # Simulated section switch: toolbar hidden.
        root.setProperty("toolbarShown", False)
        _settle(qapp)
        assert toolbar.property("visible") is False

        # Switch back: this is exactly the transition that used to get
        # permanently stuck at `visible: False` regardless of the binding.
        root.setProperty("toolbarShown", True)
        _settle(qapp)
        assert toolbar.property("visible") is True
        assert toolbar.height() > 0
        assert toolbar.width() > 0
    finally:
        for root_object in engine.rootObjects():
            root_object.deleteLater()
        QCoreApplication.processEvents()
        qml_path.unlink(missing_ok=True)
