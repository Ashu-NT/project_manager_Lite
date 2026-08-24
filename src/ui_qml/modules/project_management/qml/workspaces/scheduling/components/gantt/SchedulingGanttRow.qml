pragma ComponentBehavior: Bound

import QtQuick
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    required property string taskId
    required property var rowData
    required property string code
    required property string name
    required property string wbsCode
    required property int depth
    required property bool isSummary
    required property int childCount
    required property bool isExpanded
    required property var startDayOrdinal
    required property var finishDayOrdinal
    required property bool isMilestone
    required property bool isCritical
    required property bool isInfeasible
    required property real percentComplete
    required property string status
    required property var baselineData

    property var columns: []
    property var columnWidths: ({})
    property real gridWidth: 0
    property real gridContentWidth: 0
    property real gridContentX: 0
    property real timelineX: 0
    property real timelineWidth: 0
    property real timelineContentX: 0
    property int axisStartDay: -1
    property real pixelsPerDay: 12
    property bool showGrid: true
    property bool showTimeline: true
    property bool hierarchyMode: true
    property bool selected: false
    property bool highlightCriticalTasks: true

    signal selectionRequested(string taskId)
    signal activationRequested(string taskId)
    signal expansionRequested(string taskId, bool expanded)
    signal timelinePanRequested(real deltaX)

    function cellText(key) {
        switch (String(key || "")) {
        case "activityCode": return root.code || "-"
        case "wbs": return root.wbsCode || "-"
        case "taskName": return root.name
        case "start": return root.rowData.startDate
            ? String(root.rowData.startDate)
            : "Unscheduled"
        case "finish": return String(root.rowData.finishDate || "-")
        case "duration": return root.rowData.durationDays === null || root.rowData.durationDays === undefined ? "-" : String(root.rowData.durationDays) + "d"
        case "remainingDuration": return root.rowData.remainingDurationDays === null || root.rowData.remainingDurationDays === undefined ? "-" : String(root.rowData.remainingDurationDays) + "d"
        case "float": return root.rowData.totalFloatDays === null || root.rowData.totalFloatDays === undefined ? "-" : String(root.rowData.totalFloatDays) + "d"
        case "critical": return root.isInfeasible ? "Infeasible" : (root.isCritical ? "Critical" : "No")
        case "constraint": return String(root.rowData.constraintTypeLabel || "-")
        case "calendar": return "-"
        case "progress": return String(Math.round(root.percentComplete)) + "%"
        case "status": return String(root.rowData.statusLabel || root.status || "-")
        default: return "-"
        }
    }

    height: Theme.AppTheme.compactRowHeight

    Rectangle {
        anchors.fill: parent
        color: root.selected
            ? Theme.AppTheme.navSelectedBackground
            : rowHover.hovered
                ? Theme.AppTheme.hoverSurface
                : "transparent"
    }

    HoverHandler { id: rowHover }

    Item {
        x: 0
        width: root.gridWidth
        height: parent.height
        visible: root.showGrid
        clip: true

        TapHandler {
            onTapped: root.selectionRequested(root.taskId)
            onDoubleTapped: root.activationRequested(root.taskId)
        }

        Row {
            x: -root.gridContentX
            width: root.gridContentWidth
            height: parent.height

            Repeater {
                model: root.columns

                delegate: Rectangle {
                    id: gridCell
                    required property var modelData

                    width: Number(root.columnWidths[gridCell.columnKey] || 100)
                    height: root.height
                    color: "transparent"
                    border.color: Theme.AppTheme.divider
                    border.width: 1

                    readonly property string columnKey: String(gridCell.modelData.key || "")
                    readonly property bool isTaskName: columnKey === "taskName"
                    readonly property real hierarchyInset: isTaskName && root.hierarchyMode
                        ? root.depth * 16
                        : 0

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.AppTheme.spacingSm + gridCell.hierarchyInset
                        anchors.rightMargin: Theme.AppTheme.spacingSm
                        spacing: Theme.AppTheme.spacingXs

                        Item {
                            width: gridCell.isTaskName && root.hierarchyMode && root.isSummary ? 18 : 0
                            height: parent.height
                            visible: width > 0

                            Rectangle {
                                anchors.centerIn: parent
                                width: 16
                                height: 16
                                radius: Theme.AppTheme.radiusSm
                                color: summaryHover.hovered ? Theme.AppTheme.hoverSurface : "transparent"
                                border.color: Theme.AppTheme.subtleBorder

                                AppControls.Label {
                                    anchors.centerIn: parent
                                    text: root.isExpanded ? "-" : "+"
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }

                                HoverHandler { id: summaryHover }
                                TapHandler {
                                    onTapped: root.expansionRequested(root.taskId, !root.isExpanded)
                                }
                            }
                        }

                        AppControls.Label {
                            anchors.verticalCenter: parent.verticalCenter
                            width: Math.max(0, parent.width - x)
                            text: root.cellText(gridCell.columnKey)
                            color: root.selected ? Theme.AppTheme.navSelectedText : Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: root.isSummary && gridCell.isTaskName
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }

    Item {
        id: timelineLane
        x: root.timelineX
        width: root.timelineWidth
        height: parent.height
        visible: root.showTimeline
        clip: true

        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: Theme.AppTheme.divider
            border.width: 1
        }

        SchedulingGanttBar {
            anchors.verticalCenter: parent.verticalCenter
            startDay: root.startDayOrdinal === null || root.startDayOrdinal === undefined ? -1 : Number(root.startDayOrdinal)
            finishDay: root.finishDayOrdinal === null || root.finishDayOrdinal === undefined ? -1 : Number(root.finishDayOrdinal)
            axisStartDay: root.axisStartDay
            pixelsPerDay: root.pixelsPerDay
            timelineContentX: root.timelineContentX
            progressPercent: root.percentComplete
            taskLabel: root.name
            isSummary: root.isSummary
            isMilestone: root.isMilestone
            isCritical: root.isCritical
            isInfeasible: root.isInfeasible
            highlightCriticalTasks: root.highlightCriticalTasks
            selected: root.selected
        }

        SchedulingGanttBaseline {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 3
            startDay: root.baselineData.startDayOrdinal === null
                || root.baselineData.startDayOrdinal === undefined
                ? -1
                : Number(root.baselineData.startDayOrdinal)
            finishDay: root.baselineData.finishDayOrdinal === null
                || root.baselineData.finishDayOrdinal === undefined
                ? -1
                : Number(root.baselineData.finishDayOrdinal)
            axisStartDay: root.axisStartDay
            pixelsPerDay: root.pixelsPerDay
            timelineContentX: root.timelineContentX
            isMilestone: root.baselineData.isMilestone === true
            taskLabel: root.name
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            hoverEnabled: true

            property real lastX: 0
            property bool didPan: false

            onPressed: function(mouse) {
                lastX = mouse.x
                didPan = false
            }
            onPositionChanged: function(mouse) {
                if (!pressed) return
                const delta = mouse.x - lastX
                if (Math.abs(delta) >= 1) {
                    didPan = true
                    root.timelinePanRequested(delta)
                    lastX = mouse.x
                }
            }
            onClicked: {
                if (!didPan) root.selectionRequested(root.taskId)
            }
            onDoubleClicked: {
                if (!didPan) root.activationRequested(root.taskId)
            }
        }
    }
}
