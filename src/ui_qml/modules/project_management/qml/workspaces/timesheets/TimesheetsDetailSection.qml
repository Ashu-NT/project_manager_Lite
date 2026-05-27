import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var reviewDetail: ({
        "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "", "fields": [], "state": {}
    })
    property var entriesModel: ({
        "title": "", "subtitle": "", "emptyState": "", "items": []
    })
    property var selectedEntry: ({
        "title": "", "subtitle": "", "emptyState": "", "fields": [], "state": {}
    })
    property string selectedEntryId: ""
    property bool isBusy: false
    property var detailPage: null

    signal entrySelected(string entryId)

    readonly property bool _hasPeriod: String(root.reviewDetail.title || "").length > 0
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property int _activeSectionH: {
        if (root._idx === 0) return _sec0.implicitHeight
        if (root._idx === 1) return _sec1.implicitHeight
        if (root._idx === 2) return _sec2.implicitHeight
        return _sec3.implicitHeight
    }

    readonly property var _entryColumns: [
        { "key": "title",         "label": "Date",               "flex": 0, "minWidth": 110 },
        { "key": "subtitle",      "label": "Task / Assignment",  "flex": 2 },
        { "key": "metaText",      "label": "Hours",              "flex": 0, "minWidth": 80 },
        { "key": "statusLabel",   "label": "Status",             "flex": 0, "minWidth": 100, "type": "status" },
        { "key": "supportingText","label": "Notes",              "flex": 1 }
    ]

    implicitHeight: _activeSectionH

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 0
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Entries"
                }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: !root._hasPeriod
                    message: root.reviewDetail.emptyState || "Select a timesheet period to review its captured entries."
                }

                Item {
                    width: parent.width
                    height: 240
                    visible: root._hasPeriod

                    AppWidgets.DataTable {
                        anchors.fill: parent
                        columns: root._entryColumns
                        rows: root.entriesModel.items || []
                        loading: root.isBusy
                        emptyText: root.entriesModel.emptyState || "No time entries for this period."
                        selectedRowId: root.selectedEntryId

                        onRowSelected: function(rowId) { root.entrySelected(rowId) }
                        onRowActivated: function(rowId) { root.entrySelected(rowId) }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Theme.AppTheme.divider
                    visible: root._hasPeriod
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec1
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 1
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Approval History"
                }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: !root._hasPeriod
                    message: "Select a timesheet period to review its approval history."
                }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: root._hasPeriod && (root.reviewDetail.fields || []).length === 0
                    message: root.reviewDetail.emptyState || "No approval events recorded for this period."
                }

                Repeater {
                    model: root._hasPeriod ? (root.reviewDetail.fields || []) : []

                    delegate: Item {
                        id: _historyRow
                        required property var modelData
                        width: root.width
                        implicitHeight: _historyContent.implicitHeight + Theme.AppTheme.spacingMd * 2

                        ColumnLayout {
                            id: _historyContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Theme.AppTheme.spacingMd
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_historyRow.modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_historyRow.modelData.value || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible: String(_historyRow.modelData.supportingText || "").length > 0
                                text: String(_historyRow.modelData.supportingText || "")
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WordWrap
                            }
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: Theme.AppTheme.divider
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Theme.AppTheme.divider
                    visible: root._hasPeriod && (root.reviewDetail.fields || []).length > 0
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 2
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Labor Notes"
                }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: (root.selectedEntry.fields || []).length === 0
                    message: root.selectedEntry.emptyState || "Select a time entry from the Entries section to view its labor notes."
                }

                Repeater {
                    model: root.selectedEntry.fields || []

                    delegate: Item {
                        id: _noteRow
                        required property var modelData
                        width: root.width
                        implicitHeight: _noteContent.implicitHeight + Theme.AppTheme.spacingMd * 2

                        ColumnLayout {
                            id: _noteContent
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Theme.AppTheme.spacingMd
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_noteRow.modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_noteRow.modelData.value || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                wrapMode: Text.WordWrap
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible: String(_noteRow.modelData.supportingText || "").length > 0
                                text: String(_noteRow.modelData.supportingText || "")
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WordWrap
                            }
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: Theme.AppTheme.divider
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Theme.AppTheme.divider
                    visible: (root.selectedEntry.fields || []).length > 0
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec3
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 3
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Audit Trail"
                }

                AppWidgets.EmptyState {
                    width: parent.width
                    message: !root._hasPeriod
                        ? "Select a timesheet period to view its audit trail."
                        : "No audit events recorded for this period."
                }
            }
        }
    }
}
