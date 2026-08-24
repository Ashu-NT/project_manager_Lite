pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import "GanttGeometry.js" as Geometry

Item {
    id: root

    property var workspaceController: null
    property var ganttModel: workspaceController ? workspaceController.ganttRowsModel : null
    property var axisModel: workspaceController ? workspaceController.ganttTimeAxis : null
    property var columns: []
    property string requestedViewMode: "split"
    property string selectedActivityId: ""
    property bool dependencyLinesEnabled: workspaceController
        ? workspaceController.showDependencyLines
        : true
    property bool highlightCriticalTasks: workspaceController
        ? workspaceController.highlightCriticalTasks
        : true
    property real requestedSplitRatio: 0.5
    property real _splitDragStartRatio: 0.5
    property real _dragSplitRatio: 0.5
    property bool _splitDragging: false
    property real _centerAnchorDay: -1
    property real _previousTimelineWidth: 0
    property bool _restoringCenter: false

    readonly property bool compact: root.width <= Theme.AppTheme.compactContentBreakpoint
    readonly property real minimumGridWidth: 420
    readonly property real minimumTimelineWidth: 360
    readonly property real splitMinimumWidth: minimumGridWidth + minimumTimelineWidth + 6
    readonly property bool splitAvailable: !root.compact && root.width >= root.splitMinimumWidth
    readonly property string effectiveViewMode: root.requestedViewMode === "split"
        && !root.splitAvailable
        ? "grid"
        : root.requestedViewMode
    readonly property bool showGrid: root.effectiveViewMode !== "timeline"
    readonly property bool showTimeline: root.effectiveViewMode !== "grid"
    readonly property real splitterWidth: root.effectiveViewMode === "split" ? 6 : 0
    readonly property real effectiveSplitRatio: root._splitDragging
        ? root._dragSplitRatio
        : root._clampSplitRatio(root.requestedSplitRatio)
    readonly property real gridWidth: root.effectiveViewMode === "grid"
        ? root.width
        : root.effectiveViewMode === "timeline"
            ? 0
            : Math.max(
                root.minimumGridWidth,
                Math.min(
                    root.width * root.effectiveSplitRatio,
                    root.width - root.minimumTimelineWidth - root.splitterWidth
                )
            )
    readonly property real timelineX: root.showGrid ? root.gridWidth + root.splitterWidth : 0
    readonly property real timelineWidth: root.showTimeline
        ? Math.max(0, root.width - root.timelineX)
        : 0
    readonly property var visibleColumns: (root.columns || []).filter(function(column) {
        return column.visible !== false
    })
    readonly property var columnWidths: root._buildColumnWidths()
    readonly property real gridContentWidth: root._columnContentWidth()
    readonly property int axisStartDay: root.axisModel ? root.axisModel.rangeStartDay : -1
    readonly property int axisFinishDay: root.axisModel ? root.axisModel.rangeFinishDay : -1
    readonly property real pixelsPerDay: root.axisModel ? root.axisModel.pixelsPerDay : 0
    readonly property real timelineContentWidth: root.axisModel
        ? root.axisModel.contentWidth
        : 0
    readonly property real timelineContentX: timelineAxis.contentX
    readonly property int activeDelegateCount: rowsViewport.activeDelegateCount
    readonly property int dependencyCandidateEdgeCount: dependencyLayer.candidateEdgeCount
    readonly property bool dependencyDensitySuppressed: dependencyLayer.densitySuppressed
    readonly property string dependencyStatusMessage: dependencyLayer.statusMessage

    signal activitySelected(string taskId)
    signal activityActivated(string taskId)
    signal sortRequested(string key, int direction)
    signal splitRatioCommitted(real ratio)
    signal hierarchyExpansionRequested(string taskId, bool expanded)

    function _clampSplitRatio(ratio) {
        if (root.width <= 0) return 0.5
        const minimum = root.minimumGridWidth / root.width
        const maximum = (root.width - root.minimumTimelineWidth - 6) / root.width
        return Math.max(minimum, Math.min(maximum, Number(ratio)))
    }

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

    function _currentCenterDay(widthOverride) {
        if (!root.axisModel || !root.axisModel.hasRange || root.pixelsPerDay <= 0)
            return -1
        const viewportWidth = widthOverride === undefined
            ? root.timelineWidth
            : Number(widthOverride)
        return root.axisStartDay
            + (timelineAxis.contentX + Math.max(0, viewportWidth) / 2) / root.pixelsPerDay
    }

    function _centerOnDay(dayOrdinal) {
        if (!root.axisModel || !root.axisModel.hasRange || root.timelineWidth <= 0)
            return
        const boundedDay = Math.max(
            root.axisStartDay,
            Math.min(root.axisFinishDay, Number(dayOrdinal))
        )
        const requestedX = (boundedDay - root.axisStartDay)
            * root.pixelsPerDay - root.timelineWidth / 2
        const wasRestoringCenter = root._restoringCenter
        root._restoringCenter = true
        timelineAxis.contentX = Math.max(
            0,
            Math.min(
                Math.max(0, root.timelineContentWidth - root.timelineWidth),
                requestedX
            )
        )
        root._restoringCenter = wasRestoringCenter
        root._centerAnchorDay = boundedDay
        root._syncAxisViewport()
    }

    function _syncAxisViewport() {
        if (root.axisModel)
            root.axisModel.updateViewport(timelineAxis.contentX, root.timelineWidth)
    }

    function _applyAxisChange(callback) {
        if (!root.axisModel) return false
        const centerDay = root._currentCenterDay()
        if (centerDay > 0) root._centerAnchorDay = centerDay
        root._restoringCenter = true
        const changed = callback()
        Qt.callLater(function() {
            if (root._centerAnchorDay > 0)
                root._centerOnDay(root._centerAnchorDay)
            else
                root._syncAxisViewport()
            root._restoringCenter = false
        })
        return changed
    }

    function setTimescale(timescale) {
        return root._applyAxisChange(function() {
            return root.workspaceController
                ? root.workspaceController.setGanttTimescale(timescale)
                : root.axisModel.setTimescale(timescale)
        })
    }

    function zoomIn() {
        return root._applyAxisChange(function() {
            return root.workspaceController
                ? root.workspaceController.ganttZoomIn()
                : root.axisModel.zoomIn()
        })
    }

    function zoomOut() {
        return root._applyAxisChange(function() {
            return root.workspaceController
                ? root.workspaceController.ganttZoomOut()
                : root.axisModel.zoomOut()
        })
    }

    function resetZoom() {
        return root._applyAxisChange(function() {
            return root.workspaceController
                ? root.workspaceController.resetGanttZoom()
                : root.axisModel.resetZoom()
        })
    }

    function goToToday() {
        if (!root.axisModel || !root.axisModel.todayAvailable) return false
        root._centerOnDay(root.axisModel.todayDay + 0.5)
        return true
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
        timelineContentX: timelineAxis.contentX
        axisModel: root.axisModel
        sortKey: root.workspaceController ? root.workspaceController.activitySortKey : "schedule"
        sortDirection: root.workspaceController
            ? root.workspaceController.activitySortDirection
            : Qt.AscendingOrder
        showGrid: root.showGrid
        showTimeline: root.showTimeline
        onSortRequested: function(key, direction) { root.sortRequested(key, direction) }
    }

    Item {
        id: timelineContextLayer
        objectName: "ganttTimelineContextLayer"
        x: root.timelineX
        y: ganttHeader.height
        width: root.timelineWidth
        height: Math.max(0, root.height - y - Theme.AppTheme.spacingMd)
        visible: root.showTimeline && root.axisModel && root.axisModel.hasRange
        clip: true

        Item {
            x: -timelineAxis.contentX
            width: root.timelineContentWidth
            height: parent.height

            Repeater {
                model: root.axisModel ? root.axisModel.visibleNonWorkingIntervals : []

                delegate: Rectangle {
                    id: nonWorkingInterval
                    required property var modelData

                    x: Geometry.dayStartX(
                        nonWorkingInterval.modelData.startDay,
                        root.axisStartDay,
                        root.pixelsPerDay
                    )
                    width: Geometry.inclusiveWidth(
                        nonWorkingInterval.modelData.startDay,
                        nonWorkingInterval.modelData.finishDay,
                        root.pixelsPerDay
                    )
                    height: parent.height
                    color: Theme.AppTheme.surfaceOverlay
                    opacity: 0.7
                }
            }
        }
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
        highlightCriticalTasks: root.highlightCriticalTasks
        onSelectionRequested: function(taskId) { root.activitySelected(taskId) }
        onActivationRequested: function(taskId) { root.activityActivated(taskId) }
        onExpansionRequested: function(taskId, expanded) {
            root.hierarchyExpansionRequested(taskId, expanded)
            if (root.workspaceController !== null)
                root.workspaceController.setGanttExpanded(taskId, expanded)
        }
        onTimelinePanRequested: function(deltaX) { root._panTimeline(deltaX) }
    }

    SchedulingGanttDependencyLayer {
        id: dependencyLayer
        objectName: "ganttDependencyLayer"
        x: root.timelineX
        y: ganttHeader.height
        width: root.timelineWidth
        height: Math.max(0, root.height - y - Theme.AppTheme.spacingMd)
        visible: root.showTimeline
        clip: true
        z: 1
        ganttModel: root.ganttModel
        firstRenderedIndex: rowsViewport.firstRenderedIndex
        lastRenderedIndex: rowsViewport.lastRenderedIndex
        rowHeight: rowsViewport.rowHeight
        verticalContentY: rowsViewport.verticalContentY
        verticalOriginY: rowsViewport.verticalOriginY
        axisStartDay: root.axisStartDay
        pixelsPerDay: root.pixelsPerDay
        timelineContentX: timelineAxis.contentX
        selectedTaskId: root.selectedActivityId
        dependencyLinesEnabled: root.dependencyLinesEnabled && root.showTimeline
    }

    Rectangle {
        id: todayMarker
        objectName: "ganttTodayMarker"
        x: root.timelineX + (root.axisModel
            ? Geometry.dayCenterX(
                root.axisModel.todayDay, root.axisStartDay, root.pixelsPerDay
            )
            : 0)
            - timelineAxis.contentX
        y: ganttHeader.height
        width: 2
        height: Math.max(0, root.height - y - Theme.AppTheme.spacingMd)
        visible: root.showTimeline
            && root.axisModel
            && root.axisModel.todayAvailable
            && x >= root.timelineX
            && x <= root.timelineX + root.timelineWidth
        color: Theme.AppTheme.danger
        opacity: 0.8
        z: 2
    }

    AppControls.Label {
        anchors.centerIn: rowsViewport
        visible: root.showTimeline
            && root.ganttModel
            && root.ganttModel.rowCountValue > 0
            && (!root.axisModel || !root.axisModel.hasRange)
        text: "No scheduled dates are available for this project."
        color: Theme.AppTheme.textMuted
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.smallSize
        z: 2
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
        contentWidth: Math.max(width, root.timelineContentWidth)
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
                if (active) {
                    root._splitDragging = true
                    root._splitDragStartRatio = root.effectiveSplitRatio
                    root._dragSplitRatio = root._splitDragStartRatio
                } else if (root._splitDragging) {
                    root._splitDragging = false
                    root.splitRatioCommitted(root._clampSplitRatio(root._dragSplitRatio))
                }
            }
            onActiveTranslationChanged: {
                if (!root._splitDragging || root.width <= 0) return
                root._dragSplitRatio = root._clampSplitRatio(
                    root._splitDragStartRatio + activeTranslation.x / root.width
                )
            }
        }
    }

    onTimelineContentXChanged: {
        if (!root._restoringCenter && root.timelineWidth > 0)
            root._centerAnchorDay = root._currentCenterDay()
        root._syncAxisViewport()
    }

    onTimelineWidthChanged: {
        if (!root._restoringCenter
                && root._previousTimelineWidth > 0
                && root.axisModel
                && root.axisModel.hasRange) {
            root._centerAnchorDay = root._currentCenterDay(root._previousTimelineWidth)
            root._restoringCenter = true
        }
        root._previousTimelineWidth = root.timelineWidth
        Qt.callLater(function() {
            if (root.timelineWidth > 0 && root._centerAnchorDay > 0)
                root._centerOnDay(root._centerAnchorDay)
            else
                root._syncAxisViewport()
            root._restoringCenter = false
        })
    }

    Connections {
        target: root.axisModel

        function onConfigurationChanged() {
            Qt.callLater(function() {
                if (root._centerAnchorDay > 0)
                    root._centerOnDay(root._centerAnchorDay)
                else
                    root._syncAxisViewport()
            })
        }
    }

    Component.onCompleted: {
        root._previousTimelineWidth = root.timelineWidth
        root._syncAxisViewport()
    }
}
