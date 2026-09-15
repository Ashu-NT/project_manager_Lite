pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Flickable {
    id: root

    property var items: []

    // Fixed 3-value attention category -- mapped explicitly.
    function _categoryTone(category) {
        const c = String(category || "").toLowerCase()
        if (c === "risk") return "danger"
        if (c === "delayed") return "warning"
        if (c === "approval") return "info"
        return "neutral"
    }
    // Row statusLabel is a union across the 3 attention row sources
    // (delayed-task watchlist, high-risk register entries, pending
    // approvals) -- mapped explicitly per value, not inferred from text.
    function _rowStatusTone(statusLabel) {
        const s = String(statusLabel || "").toLowerCase()
        if (s === "blocked" || s === "late" || s === "critical" || s === "rejected") return "danger"
        if (s === "tight float" || s === "pending" || s === "open") return "warning"
        if (s === "in progress" || s === "tracked") return "info"
        if (s === "mitigated" || s === "approved" || s === "closed") return "success"
        return "neutral"
    }

    contentWidth: width
    contentHeight: _col.implicitHeight + Theme.AppTheme.spacingSm * 2
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    AppWidgets.EmptyState {
        anchors.centerIn: parent
        width: parent.width - Theme.AppTheme.marginLg * 2
        visible: root.items.length === 0
        title: "Nothing needs attention"
        message: "No delayed tasks, high risks, or pending approvals right now."
    }

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.AppTheme.spacingSm
        spacing: Theme.AppTheme.spacingSm
        visible: root.items.length > 0

        Repeater {
            model: root.items

            delegate: Rectangle {
                id: _row
                required property var modelData
                Layout.fillWidth: true
                implicitHeight: _rowLayout.implicitHeight + Theme.AppTheme.spacingSm * 2
                radius: Theme.AppTheme.radiusSm
                color: Theme.AppTheme.surfaceAlt
                border.color: Theme.AppTheme.subtleBorder
                border.width: 1

                RowLayout {
                    id: _rowLayout
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.spacingSm
                    spacing: Theme.AppTheme.spacingSm

                    AppWidgets.StatusChip {
                        status: String(_row.modelData.category || "")
                        tone:   root._categoryTone(_row.modelData.category || "")
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_row.modelData.title || "")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                            elide: Text.ElideRight
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_row.modelData.subtitle || "")
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            elide: Text.ElideRight
                        }
                    }

                    AppWidgets.StatusChip {
                        status: String(_row.modelData.statusLabel || "")
                        tone:   root._rowStatusTone(_row.modelData.statusLabel || "")
                    }
                }
            }
        }
    }
}
