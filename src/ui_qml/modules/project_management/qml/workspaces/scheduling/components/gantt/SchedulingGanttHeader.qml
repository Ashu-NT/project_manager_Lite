pragma ComponentBehavior: Bound

import QtQuick
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var columns: []
    property var columnWidths: ({})
    property real gridWidth: 0
    property real gridContentWidth: 0
    property real gridContentX: 0
    property real timelineX: 0
    property real timelineWidth: 0
    property real timelineContentWidth: 0
    property real timelineContentX: 0
    property string timelineStartLabel: ""
    property string timelineFinishLabel: ""
    property string sortKey: "schedule"
    property int sortDirection: Qt.AscendingOrder
    property bool showGrid: true
    property bool showTimeline: true

    signal sortRequested(string key, int direction)

    height: Theme.AppTheme.normalRowHeight

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.surfaceAlt
        border.color: Theme.AppTheme.divider
        border.width: 1
    }

    Item {
        x: 0
        width: root.gridWidth
        height: parent.height
        visible: root.showGrid
        clip: true

        Row {
            x: -root.gridContentX
            width: root.gridContentWidth
            height: parent.height

            Repeater {
                model: root.columns

                delegate: Rectangle {
                    id: columnHeader
                    required property var modelData

                    width: Number(root.columnWidths[columnHeader.columnKey] || 100)
                    height: root.height
                    color: headerHover.hovered ? Theme.AppTheme.hoverSurface : "transparent"
                    border.color: Theme.AppTheme.divider
                    border.width: 1

                    readonly property string columnKey: String(columnHeader.modelData.key || "")
                    readonly property bool canSort: columnHeader.modelData.sortable !== false
                        && columnHeader.columnKey.length > 0

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.AppTheme.spacingSm
                        anchors.rightMargin: Theme.AppTheme.spacingXs
                        spacing: Theme.AppTheme.spacingXs

                        AppControls.Label {
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.max(0, parent.width - sortLabel.width - parent.spacing)
                            text: String(columnHeader.modelData.label || columnHeader.columnKey)
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                            elide: Text.ElideRight
                        }

                        AppControls.Label {
                            id: sortLabel
                            anchors.verticalCenter: parent.verticalCenter
                            visible: root.sortKey === columnHeader.columnKey
                            text: root.sortDirection === Qt.DescendingOrder ? "DESC" : "ASC"
                            color: Theme.AppTheme.accent
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }

                    HoverHandler { id: headerHover }
                    TapHandler {
                        enabled: columnHeader.canSort
                        onTapped: {
                            const direction = root.sortKey === columnHeader.columnKey
                                && root.sortDirection === Qt.AscendingOrder
                                ? Qt.DescendingOrder
                                : Qt.AscendingOrder
                            root.sortRequested(columnHeader.columnKey, direction)
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        x: root.timelineX
        width: root.timelineWidth
        height: parent.height
        visible: root.showTimeline
        clip: true
        color: "transparent"
        border.color: Theme.AppTheme.divider
        border.width: 1

        Item {
            x: -root.timelineContentX
            width: root.timelineContentWidth
            height: parent.height

            AppControls.Label {
                x: 16
                anchors.verticalCenter: parent.verticalCenter
                text: root.timelineStartLabel || "Schedule start"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
            }

            AppControls.Label {
                x: Math.max(16, parent.width - implicitWidth - 16)
                anchors.verticalCenter: parent.verticalCenter
                text: root.timelineFinishLabel || "Schedule finish"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
            }

            AppControls.Label {
                anchors.centerIn: parent
                text: "Current schedule"
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
            }
        }
    }
}
