pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var detailModel: ({
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "fields": [],
        "activity": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
        "relatedItems": { "title": "", "subtitle": "", "emptyState": "", "items": [] },
        "audit": { "title": "", "subtitle": "", "emptyState": "", "items": [] }
    })
    property var detailPage: null
    property bool isBusy: false

    signal relatedItemActivated(var itemData)
    signal activityItemActivated(var itemData)
    signal auditItemActivated(var itemData)

    readonly property bool _hasDetail: String(root.detailModel.id || "").length > 0
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0

    implicitHeight: (_summaryStrip.visible ? _summaryStrip.height : 0)
        + _activeSectionH
        + Theme.AppTheme.spacingLg
    height: implicitHeight

    readonly property int _activeSectionH: {
        if (root._idx === 0) return _sec0.implicitHeight
        if (root._idx === 1) return _sec1.implicitHeight
        if (root._idx === 2) return _sec2.implicitHeight
        return _sec3.implicitHeight
    }

    readonly property var _relatedColumns: [
        { "key": "title", "label": "Related Item", "preferredWidth": 260, "sortable": true },
        { "key": "statusLabel", "label": "Type", "preferredWidth": 120, "type": "status" },
        { "key": "subtitle", "label": "Reference", "preferredWidth": 220 },
        { "key": "supportingText", "label": "Summary", "preferredWidth": 260 }
    ]

    Rectangle {
        id: _summaryStrip
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 40
        color: Theme.AppTheme.surfaceAlt
        visible: root._hasDetail

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Theme.AppTheme.divider
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.AppTheme.marginMd
            anchors.rightMargin: Theme.AppTheme.marginMd
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.StatusChip {
                visible: String(root.detailModel.statusLabel || "").length > 0
                status: root.detailModel.statusLabel || ""
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: root.detailModel.subtitle || ""
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                elide: Text.ElideRight
                visible: text.length > 0
            }
        }
    }

    Item {
        id: _sectionArea
        anchors.top: _summaryStrip.visible ? _summaryStrip.bottom : parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: root._activeSectionH

        AppWidgets.LazySectionLoader {
            id: _sec0
            active: root._idx === 0
            sourceComponent: Component {
                Item {
                    width: parent ? parent.width : 0
                    implicitHeight: _overviewCol.implicitHeight + Theme.AppTheme.spacingMd * 2

                    ColumnLayout {
                        id: _overviewCol
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.marginMd
                        anchors.rightMargin: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingMd

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: !root._hasDetail
                            title: "Select an inbox, mention, approval, or activity item to inspect details."
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: root._hasDetail && String(root.detailModel.description || "").length > 0
                            text: root.detailModel.description || ""
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            wrapMode: Text.WordWrap
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            visible: root._hasDetail && (root.detailModel.fields || []).length > 0
                            columns: 2
                            columnSpacing: Theme.AppTheme.spacingLg
                            rowSpacing: Theme.AppTheme.spacingMd

                            Repeater {
                                model: root.detailModel.fields || []

                                delegate: ColumnLayout {
                                    required property var modelData

                                    Layout.fillWidth: true
                                    spacing: 2

                                    AppControls.Label {
                                        text: String(modelData.label || "")
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold: true
                                    }

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(modelData.value || "—")
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec1
            active: root._idx === 1
            sourceComponent: Component {
                Item {
                    width: parent ? parent.width : 0
                    implicitHeight: _activityCol.implicitHeight + Theme.AppTheme.spacingMd * 2

                    ColumnLayout {
                        id: _activityCol
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.marginMd
                        anchors.rightMargin: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingMd

                        AppWidgets.ActivityFeed {
                            Layout.fillWidth: true
                            items: root.detailModel.activity ? (root.detailModel.activity.items || []) : []
                            emptyText: root.detailModel.activity
                                ? (root.detailModel.activity.emptyState || "No related activity is available.")
                                : "No related activity is available."
                            onItemActivated: function(itemData) {
                                root.activityItemActivated(itemData)
                            }
                        }
                    }
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec2
            active: root._idx === 2
            sourceComponent: Component {
                Item {
                    width: parent ? parent.width : 0
                    implicitHeight: _relatedTable.implicitHeight + Theme.AppTheme.spacingMd * 2

                    AppWidgets.DataTable {
                        id: _relatedTable
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.marginMd
                        anchors.rightMargin: Theme.AppTheme.marginMd
                        implicitHeight: 220
                        columns: root._relatedColumns
                        emptyText: root.detailModel.relatedItems
                            ? (root.detailModel.relatedItems.emptyState || "No related items are available.")
                            : "No related items are available."
                        loading: root.isBusy
                        onRowActivated: function(rowId) {
                            const rows = root.detailModel.relatedItems ? (root.detailModel.relatedItems.items || []) : []
                            for (let i = 0; i < rows.length; i += 1) {
                                if (String(rows[i].id || "") === String(rowId || "")) {
                                    root.relatedItemActivated(rows[i])
                                    break
                                }
                            }
                        }
                    }
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec3
            active: root._idx === 3
            sourceComponent: Component {
                Item {
                    width: parent ? parent.width : 0
                    implicitHeight: _auditCol.implicitHeight + Theme.AppTheme.spacingMd * 2

                    ColumnLayout {
                        id: _auditCol
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.marginMd
                        anchors.rightMargin: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingMd

                        AppWidgets.ActivityFeed {
                            Layout.fillWidth: true
                            items: root.detailModel.audit ? (root.detailModel.audit.items || []) : []
                            emptyText: root.detailModel.audit
                                ? (root.detailModel.audit.emptyState || "No related audit events are available.")
                                : "No related audit events are available."
                            onItemActivated: function(itemData) {
                                root.auditItemActivated(itemData)
                            }
                        }
                    }
                }
            }
        }
    }
}
