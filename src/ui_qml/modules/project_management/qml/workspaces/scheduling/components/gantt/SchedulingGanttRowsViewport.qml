pragma ComponentBehavior: Bound

import QtQuick
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var ganttModel: null
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
    property string selectedActivityId: ""
    property bool highlightCriticalTasks: true
    readonly property int rowHeight: Theme.AppTheme.compactRowHeight
    readonly property int activeDelegateCount: _delegateCount
    readonly property real verticalContentY: rowsList.contentY
    readonly property real verticalOriginY: rowsList.originY
    readonly property int overscanRowCount: 4
    readonly property int firstVisibleIndex: ganttModel && ganttModel.rowCountValue > 0
        ? Math.max(0, Math.floor(Math.max(0, rowsList.contentY) / rowHeight))
        : -1
    readonly property int lastVisibleIndex: firstVisibleIndex >= 0
        ? Math.min(
            ganttModel.rowCountValue - 1,
            Math.ceil((Math.max(0, rowsList.contentY) + rowsList.height) / rowHeight) - 1
        )
        : -1
    readonly property int firstRenderedIndex: firstVisibleIndex >= 0
        ? Math.max(0, firstVisibleIndex - overscanRowCount)
        : -1
    readonly property int lastRenderedIndex: lastVisibleIndex >= 0
        ? Math.min(ganttModel.rowCountValue - 1, lastVisibleIndex + overscanRowCount)
        : -1
    property int _delegateCount: 0

    signal selectionRequested(string taskId)
    signal activationRequested(string taskId)
    signal expansionRequested(string taskId, bool expanded)
    signal timelinePanRequested(real deltaX)

    function revealSelection(positionRow) {
        if (root.ganttModel === null) return
        const index = root.ganttModel.indexOfTask(root.selectedActivityId)
        rowsList.currentIndex = index
        if (positionRow && index >= 0)
            rowsList.positionViewAtIndex(index, ListView.Contain)
    }

    onSelectedActivityIdChanged: revealSelection(false)

    ListView {
        id: rowsList
        objectName: "ganttRowsVerticalAuthority"
        anchors.fill: parent
        model: root.ganttModel
        clip: true
        reuseItems: true
        cacheBuffer: root.rowHeight * 4
        spacing: 0
        boundsBehavior: Flickable.StopAtBounds
        focus: true
        keyNavigationEnabled: false

        Keys.onUpPressed: function(event) {
            const current = root.ganttModel
                ? root.ganttModel.indexOfTask(root.selectedActivityId)
                : -1
            const target = Math.max(0, current < 0 ? 0 : current - 1)
            const taskId = root.ganttModel ? root.ganttModel.taskIdAt(target) : ""
            if (taskId.length > 0) {
                root.selectionRequested(taskId)
                rowsList.positionViewAtIndex(target, ListView.Contain)
            }
            event.accepted = true
        }
        Keys.onDownPressed: function(event) {
            const current = root.ganttModel
                ? root.ganttModel.indexOfTask(root.selectedActivityId)
                : -1
            const target = current < 0 ? 0 : current + 1
            const taskId = root.ganttModel ? root.ganttModel.taskIdAt(target) : ""
            if (taskId.length > 0) {
                root.selectionRequested(taskId)
                rowsList.positionViewAtIndex(target, ListView.Contain)
            }
            event.accepted = true
        }
        Keys.onReturnPressed: function(event) {
            if (root.selectedActivityId.length > 0)
                root.activationRequested(root.selectedActivityId)
            event.accepted = true
        }
        Keys.onEnterPressed: function(event) {
            if (root.selectedActivityId.length > 0)
                root.activationRequested(root.selectedActivityId)
            event.accepted = true
        }

        delegate: SchedulingGanttRow {
            id: ganttRow

            width: rowsList.width
            columns: root.columns
            columnWidths: root.columnWidths
            gridWidth: root.gridWidth
            gridContentWidth: root.gridContentWidth
            gridContentX: root.gridContentX
            timelineX: root.timelineX
            timelineWidth: root.timelineWidth
            timelineContentX: root.timelineContentX
            axisStartDay: root.axisStartDay
            pixelsPerDay: root.pixelsPerDay
            showGrid: root.showGrid
            showTimeline: root.showTimeline
            hierarchyMode: root.ganttModel ? root.ganttModel.hierarchyMode : true
            selected: root.selectedActivityId.length > 0
                && root.selectedActivityId === ganttRow.taskId
            highlightCriticalTasks: root.highlightCriticalTasks

            onSelectionRequested: function(taskId) {
                rowsList.forceActiveFocus()
                root.selectionRequested(taskId)
            }
            onActivationRequested: function(taskId) { root.activationRequested(taskId) }
            onExpansionRequested: function(taskId, expanded) {
                root.expansionRequested(taskId, expanded)
            }
            onTimelinePanRequested: function(deltaX) { root.timelinePanRequested(deltaX) }

            Component.onCompleted: root._delegateCount += 1
            Component.onDestruction: root._delegateCount = Math.max(0, root._delegateCount - 1)
        }
    }

    AppControls.Label {
        anchors.centerIn: parent
        visible: root.ganttModel === null || root.ganttModel.rowCountValue === 0
        text: "No activities match the current planning view."
        color: Theme.AppTheme.textMuted
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.smallSize
    }
}
