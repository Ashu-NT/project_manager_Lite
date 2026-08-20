pragma ComponentBehavior: Bound

import QtQuick
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var columns: []
    property var columnWidths: ({})
    property var axisModel: null
    property real gridWidth: 0
    property real gridContentWidth: 0
    property real gridContentX: 0
    property real timelineX: 0
    property real timelineWidth: 0
    property real timelineContentX: 0
    property string sortKey: "schedule"
    property int sortDirection: Qt.AscendingOrder
    property bool showGrid: true
    property bool showTimeline: true

    readonly property int bandHeight: 28
    readonly property int axisStartDay: root.axisModel ? root.axisModel.rangeStartDay : -1
    readonly property real pixelsPerDay: root.axisModel ? root.axisModel.pixelsPerDay : 0

    signal sortRequested(string key, int direction)

    height: root.bandHeight * 2

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.surfaceAlt
        border.color: Theme.AppTheme.divider
        border.width: 1
    }

    Item {
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
        color: Theme.AppTheme.surfaceAlt
        border.color: Theme.AppTheme.divider
        border.width: 1

        AppControls.Label {
            anchors.centerIn: parent
            visible: !root.axisModel || !root.axisModel.hasRange
            text: "No scheduled date range"
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
        }

        Item {
            x: -root.timelineContentX
            width: root.axisModel ? root.axisModel.contentWidth : 0
            height: parent.height
            visible: root.axisModel && root.axisModel.hasRange

            Repeater {
                model: root.axisModel ? root.axisModel.majorTicks : []

                delegate: Rectangle {
                    id: majorTick
                    required property var modelData

                    x: (Number(majorTick.modelData.startDay) - root.axisStartDay)
                        * root.pixelsPerDay
                    y: 0
                    width: (Number(majorTick.modelData.finishDay)
                        - Number(majorTick.modelData.startDay) + 1) * root.pixelsPerDay
                    height: root.bandHeight
                    color: "transparent"
                    border.color: Theme.AppTheme.divider
                    border.width: 1

                    AppControls.Label {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.AppTheme.spacingXs
                        anchors.rightMargin: Theme.AppTheme.spacingXs
                        text: String(majorTick.modelData.label || "")
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                        elide: Text.ElideRight
                    }
                }
            }

            Repeater {
                model: root.axisModel ? root.axisModel.minorTicks : []

                delegate: Rectangle {
                    id: minorTick
                    required property var modelData

                    x: (Number(minorTick.modelData.startDay) - root.axisStartDay)
                        * root.pixelsPerDay
                    y: root.bandHeight
                    width: (Number(minorTick.modelData.finishDay)
                        - Number(minorTick.modelData.startDay) + 1) * root.pixelsPerDay
                    height: root.bandHeight
                    color: "transparent"
                    border.color: Theme.AppTheme.divider
                    border.width: 1

                    AppControls.Label {
                        anchors.fill: parent
                        anchors.leftMargin: 2
                        anchors.rightMargin: 2
                        text: String(minorTick.modelData.label || "")
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
