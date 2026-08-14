pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var entriesModel: ({})
    property var entriesTableModel: null
    property string selectedEntryId: ""
    property bool isBusy: false

    signal entrySelected(string entryId)

    readonly property var _items: root.entriesModel.items || []
    readonly property int _tableH: {
        const count = root._items.length
        const natural = Theme.AppTheme.normalRowHeight + Math.max(count, 1) * Theme.AppTheme.compactRowHeight + 24
        return Math.max(240, Math.min(natural, 420))
    }
    readonly property var _columns: [
        { key: "title", label: "Period / Date", flex: 2, sortable: false },
        { key: "subtitle", label: "Resource", flex: 2, sortable: false },
        { key: "metaText", label: "Hours / Note", flex: 2, sortable: false },
        { key: "statusLabel", label: "Status", flex: 0, minWidth: 90, type: "status" }
    ]
    Layout.fillWidth: true
    implicitHeight: _ledgerFrame.implicitHeight

    Rectangle {
        id: _ledgerFrame
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        implicitHeight: _ledgerColumn.implicitHeight + Theme.AppTheme.marginMd * 2
        radius: Theme.AppTheme.radiusMd
        color: Theme.AppTheme.surfaceRaised
        border.color: Theme.AppTheme.subtleBorder
        border.width: 1

        ColumnLayout {
            id: _ledgerColumn
            anchors.fill: parent
            anchors.margins: Theme.AppTheme.marginMd
            spacing: Theme.AppTheme.spacingMd

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Entry Ledger"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: root.entriesModel.subtitle || "Detailed labor entries for the selected task assignment."
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }

                Rectangle {
                    implicitWidth: _ledgerCountLabel.implicitWidth + Theme.AppTheme.spacingMd * 2
                    implicitHeight: Theme.AppTheme.toolbarHeight
                    radius: Theme.AppTheme.radiusSm
                    color: Theme.AppTheme.surfaceAlt
                    border.color: Theme.AppTheme.subtleBorder
                    border.width: 1

                    AppControls.Label {
                        id: _ledgerCountLabel
                        anchors.centerIn: parent
                        text: root._items.length > 0 ? root._items.length + " entries" : "No entries"
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.AppTheme.divider
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: root._tableH

                AppWidgets.DataTable {
                    anchors.fill: parent
                    columns: root._columns
                    sourceModel: root.entriesTableModel
                    selectedRowId: root.selectedEntryId
                    loading: root.isBusy
                    emptyText: root.entriesModel.emptyState || "No time entries for this period."

                    onRowSelected: function(rowId) {
                        root.entrySelected(rowId)
                    }
                    onRowActivated: function(rowId) {
                        root.entrySelected(rowId)
                    }
                }
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: root._items.length > 0
                    ? "Select a row to move directly into capture mode for corrections, notes, or hour adjustments."
                    : "Entries will appear here once labor is captured for the selected assignment and period."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode: Text.WordWrap
            }
        }
    }
}


