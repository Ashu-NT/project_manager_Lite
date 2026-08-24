pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import "GanttGeometry.js" as Geometry

Item {
    id: root

    property int startDay: -1
    property int finishDay: -1
    property int axisStartDay: -1
    property real pixelsPerDay: 0
    property real timelineContentX: 0
    property bool isMilestone: false
    property string taskLabel: ""

    readonly property real milestoneSize: 9
    readonly property bool hasDates: root.axisStartDay > 0
        && root.startDay >= root.axisStartDay
        && root.finishDay >= root.startDay
        && root.pixelsPerDay > 0
    readonly property real contentStartX: Geometry.dayStartX(
        root.startDay, root.axisStartDay, root.pixelsPerDay
    )
    readonly property real contentCenterX: Geometry.dayCenterX(
        root.startDay, root.axisStartDay, root.pixelsPerDay
    )
    readonly property real trackWidth: Math.max(
        8,
        Geometry.inclusiveWidth(root.startDay, root.finishDay, root.pixelsPerDay)
    )

    visible: root.hasDates
    x: (root.isMilestone
        ? root.contentCenterX - root.milestoneSize / 2
        : root.contentStartX) - root.timelineContentX
    width: root.isMilestone ? root.milestoneSize : root.trackWidth
    height: 9

    Rectangle {
        objectName: "baselineGanttShape"
        anchors.centerIn: parent
        width: root.isMilestone ? 7 : parent.width
        height: root.isMilestone ? 7 : 4
        radius: root.isMilestone ? 1 : 2
        rotation: root.isMilestone ? 45 : 0
        color: root.isMilestone ? Theme.AppTheme.surfaceOverlay : Theme.AppTheme.textMuted
        opacity: root.isMilestone ? 1 : 0.62
        border.color: Theme.AppTheme.textMuted
        border.width: root.isMilestone ? 1 : 0
    }

    HoverHandler { id: baselineHover }
    ToolTip.visible: baselineHover.hovered
    ToolTip.text: "Baseline: " + root.taskLabel
}
