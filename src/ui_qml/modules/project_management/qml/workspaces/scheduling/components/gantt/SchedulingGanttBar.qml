pragma ComponentBehavior: Bound

import QtQuick
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property int startDay: -1
    property int finishDay: -1
    property int axisStartDay: -1
    property real pixelsPerDay: 0
    property real timelineContentX: 0
    property real progressPercent: 0
    property string taskLabel: ""
    property bool isSummary: false
    property bool isMilestone: false
    property bool isCritical: false
    property bool isInfeasible: false
    property bool selected: false

    readonly property real minimumTaskPixels: 12
    readonly property real milestoneSize: 14
    readonly property bool hasDates: root.axisStartDay > 0
        && root.startDay >= root.axisStartDay
        && root.finishDay >= root.startDay
        && root.pixelsPerDay > 0
    readonly property real contentStartX: (root.startDay - root.axisStartDay)
        * root.pixelsPerDay
    readonly property real contentCenterX: (root.startDay - root.axisStartDay + 0.5)
        * root.pixelsPerDay
    readonly property real taskWidth: Math.max(
        root.minimumTaskPixels,
        (root.finishDay - root.startDay + 1) * root.pixelsPerDay
    )
    readonly property real progressWidth: root.isMilestone
        ? 0
        : Math.max(0, Math.min(root.taskWidth, root.taskWidth * root.progressPercent / 100))
    readonly property color semanticColor: root.isInfeasible
        ? Theme.AppTheme.danger
        : root.isCritical
            ? Theme.AppTheme.warning
            : Theme.AppTheme.accent

    visible: root.hasDates
    x: (root.isMilestone
        ? root.contentCenterX - root.milestoneSize / 2
        : root.contentStartX) - root.timelineContentX
    width: root.isMilestone ? root.milestoneSize : root.taskWidth
    height: 18

    Rectangle {
        id: taskShape
        anchors.centerIn: parent
        width: root.isMilestone ? 12 : parent.width
        height: root.isMilestone ? 12 : 14
        radius: root.isMilestone ? 2 : Theme.AppTheme.radiusSm
        rotation: root.isMilestone ? 45 : 0
        color: root.semanticColor
        opacity: root.isSummary ? 0.72 : 1.0
        border.color: root.selected ? Theme.AppTheme.textPrimary : "transparent"
        border.width: root.selected ? 2 : 0

        Rectangle {
            visible: !root.isMilestone
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: root.progressWidth
            radius: parent.radius
            color: Theme.AppTheme.success
            opacity: 0.55
        }
    }

    AppControls.Label {
        x: taskShape.x + taskShape.width + Theme.AppTheme.spacingXs
        anchors.verticalCenter: parent.verticalCenter
        width: 180
        text: root.taskLabel
        color: Theme.AppTheme.textSecondary
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.captionSize
        font.bold: root.isSummary
        elide: Text.ElideRight
    }
}
