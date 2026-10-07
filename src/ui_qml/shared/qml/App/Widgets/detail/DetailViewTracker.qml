pragma Singleton

import QtQuick

// Tracks how many SectionDetailPage instances (the shared entity-detail
// shell used across every module -- Platform, Project Management, and any
// future module that reuses it) are currently alive, application-wide.
// SectionDetailPage itself reports its own open/close here; no individual
// workspace page, module, or the shell needs to know about any specific
// entity's detail state -- this is the one, generic signal a shell can
// watch to know "is *some* record's detail view open right now," to
// e.g. auto-collapse the global navigation sidebar and free horizontal
// room for the detail page's own content.
QtObject {
    id: root

    property int openCount: 0
    readonly property bool anyOpen: root.openCount > 0

    function open() {
        root.openCount += 1
    }

    function close() {
        root.openCount = Math.max(0, root.openCount - 1)
    }
}
