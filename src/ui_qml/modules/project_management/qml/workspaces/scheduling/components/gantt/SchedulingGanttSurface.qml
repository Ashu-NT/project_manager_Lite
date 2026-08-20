pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var workspaceController: null
    property var ganttModel: workspaceController ? workspaceController.ganttRowsModel : null
    property var columns: []
    property string requestedViewMode: "split"
    property string selectedActivityId: ""
    property real requestedGridWidth: 760
    property real _splitDragStartWidth: 760

    readonly property bool compact: root.width <= Theme.AppTheme.compactContentBreakpoint
    readonly property real splitMinimumWidth: 960
    readonly property bool splitAvailable: !root.compact && root.width >= root.splitMinimumWidth
    readonly property string effectiveViewMode: root.requestedViewMode === "split"
        && !root.splitAvailable
        ? "grid"
        : root.requestedViewMode
    readonly property bool showGrid: root.effectiveViewMode !== "timeline"
    readonly property bool showTimeline: root.effectiveViewMode !== "grid"
    readonly property real splitterWidth: root.effectiveViewMode === "split" ? 6 : 0
    readonly property real gridWidth: root.effectiveViewMode === "grid"
        ? root.width
        : root.effectiveViewMode === "timeline"
            ? 0
            : Math.max(420, Math.min(root.requestedGridWidth, root.width - 360 - root.splitterWidth))
    readonly property real timelineX: root.showGrid ? root.gridWidth + root.splitterWidth : 0
    readonly property real timelineWidth: root.showTimeline
        ? Math.max(0, root.width - root.timelineX)
        : 0
    readonly property var visibleColumns: (root.columns || []).filter(function(column) {
        return column.visible !== false
    })
    readonly property var columnWidths: root._buildColumnWidths()
    readonly property real gridContentWidth: root._columnContentWidth()
    readonly property int axisStartDay: root.ganttModel ? root.ganttModel.timelineStartDay : -1
    readonly property int axisFinishDay: root.ganttModel ? root.ganttModel.timelineFinishDay : -1
    readonly property real pixelsPerDay: 12
    readonly property real timelineContentWidth: Math.max(
        root.timelineWidth,
        root.axisStartDay >= 0 && root.axisFinishDay >= root.axisStartDay
            ? (root.axisFinishDay - root.axisStartDay + 1) * root.pixelsPerDay + 220
            : root.timelineWidth
    )
    readonly property int activeDelegateCount: rowsViewport.activeDelegateCount
    readonly property real timelineContentX: timelineAxis.contentX
    readonly property real verticalContentY: rowsViewport.verticalContentY
    readonly property real authoritativeRowHeight: rowsViewport.rowHeight

    signal activitySelected(string taskId)
    signal activityActivated(string taskId)
    signal sortRequested(string key, int direction)

    function _columnWidth(column) {
        const key = String(column.key || "")
        const defaults = {
            "activityCode": 104,
            "wbs": 76,
            "taskName": 220,
            "start": 96,
            "finish": 96,
            "duration": 84,
            "remainingDuration": 104,
            "float": 72,
            "critical": 88,
            "constraint": 144,
            "calendar": 120,
            "progress": 112,
            "status": 104
        }
        return Math.max(Number(column.minWidth || 0), Number(defaults[key] || 100))
    }

    function _buildColumnWidths() {
        const result = {}
        for (let i = 0; i < root.visibleColumns.length; i++) {
            const column = root.visibleColumns[i]
            result[String(column.key || "")] = root._columnWidth(column)
        }
        return result
    }

    function _columnContentWidth() {
        let result = 0
        for (let i = 0; i < root.visibleColumns.length; i++)
            result += Number(root.columnWidths[String(root.visibleColumns[i].key || "")] || 100)
        return result
    }

    function _dateLabel(dayOrdinal) {
        if (dayOrdinal < 1) return ""
        const epochDay = dayOrdinal - 719163
        return new Date(epochDay * 86400000).toISOString().slice(0, 10)
    }

    function _panTimeline(deltaX) {
        timelineAxis.contentX = Math.max(
            0,
            Math.min(
                timelineAxis.contentWidth - timelineAxis.width,
                timelineAxis.contentX - deltaX
            )
        )
    }

    function revealSelectedActivity() {
        rowsViewport.revealSelection(true)
    }

    SchedulingGanttHeader {
        id: ganttHeader
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        columns: root.visibleColumns
        columnWidths: root.columnWidths
        gridWidth: root.gridWidth
        gridContentWidth: root.gridContentWidth
        gridContentX: gridAxis.contentX
        timelineX: root.timelineX
        timelineWidth: root.timelineWidth
        timelineContentWidth: root.timelineContentWidth
        timelineContentX: timelineAxis.contentX
        timelineStartLabel: root._dateLabel(root.axisStartDay)
        timelineFinishLabel: root._dateLabel(root.axisFinishDay)
        sortKey: root.workspaceController ? root.workspaceController.activitySortKey : "schedule"
        sortDirection: root.workspaceController
            ? root.workspaceController.activitySortDirection
            : Qt.AscendingOrder
        showGrid: root.showGrid
        showTimeline: root.showTimeline
        onSortRequested: function(key, direction) { root.sortRequested(key, direction) }
    }

    SchedulingGanttRowsViewport {
        id: rowsViewport
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: ganttHeader.bottom
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.AppTheme.spacingMd
        ganttModel: root.ganttModel
        columns: root.visibleColumns
        columnWidths: root.columnWidths
        gridWidth: root.gridWidth
        gridContentWidth: root.gridContentWidth
        gridContentX: gridAxis.contentX
        timelineX: root.timelineX
        timelineWidth: root.timelineWidth
        timelineContentX: timelineAxis.contentX
        axisStartDay: root.axisStartDay
        pixelsPerDay: root.pixelsPerDay
        showGrid: root.showGrid
        showTimeline: root.showTimeline
        selectedActivityId: root.selectedActivityId
        onSelectionRequested: function(taskId) { root.activitySelected(taskId) }
        onActivationRequested: function(taskId) { root.activityActivated(taskId) }
        onExpansionRequested: function(taskId, expanded) {
            if (root.workspaceController !== null)
                root.workspaceController.setGanttExpanded(taskId, expanded)
        }
        onTimelinePanRequested: function(deltaX) { root._panTimeline(deltaX) }
    }

    // These two objects own horizontal state. They contain no rows; the one
    // virtualized ListView above renders every grid cell and timeline lane.
    Flickable {
        id: gridAxis
        objectName: "ganttGridHorizontalAuthority"
        x: 0
        y: ganttHeader.height
        width: root.gridWidth
        height: Math.max(0, root.height - y)
        visible: root.showGrid
        contentWidth: Math.max(width, root.gridContentWidth)
        contentHeight: height
        interactive: false
        boundsBehavior: Flickable.StopAtBounds
        z: 3

        ScrollBar.horizontal: ScrollBar {
            policy: gridAxis.contentWidth > gridAxis.width
                ? ScrollBar.AlwaysOn
                : ScrollBar.AlwaysOff
        }
    }

    Flickable {
        id: timelineAxis
        objectName: "ganttTimelineHorizontalAuthority"
        x: root.timelineX
        y: ganttHeader.height
        width: root.timelineWidth
        height: Math.max(0, root.height - y)
        visible: root.showTimeline
        contentWidth: root.timelineContentWidth
        contentHeight: height
        interactive: false
        boundsBehavior: Flickable.StopAtBounds
        z: 3

        ScrollBar.horizontal: ScrollBar {
            policy: timelineAxis.contentWidth > timelineAxis.width
                ? ScrollBar.AlwaysOn
                : ScrollBar.AlwaysOff
        }
    }

    Rectangle {
        id: splitHandle
        x: root.gridWidth
        y: 0
        width: root.splitterWidth
        height: parent.height
        visible: root.effectiveViewMode === "split"
        color: splitHover.hovered ? Theme.AppTheme.accent : Theme.AppTheme.divider
        z: 5

        HoverHandler { id: splitHover; cursorShape: Qt.SplitHCursor }
        DragHandler {
            target: null
            xAxis.enabled: true
            yAxis.enabled: false
            onActiveChanged: {
                if (active) root._splitDragStartWidth = root.requestedGridWidth
            }
            onActiveTranslationChanged: {
                root.requestedGridWidth = Math.max(
                    420,
                    Math.min(
                        root.width - 360 - root.splitterWidth,
                        root._splitDragStartWidth + activeTranslation.x
                    )
                )
            }
        }
    }
}
