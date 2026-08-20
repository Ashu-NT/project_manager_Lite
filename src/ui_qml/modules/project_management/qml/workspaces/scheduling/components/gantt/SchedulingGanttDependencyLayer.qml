pragma ComponentBehavior: Bound

import QtQuick
import App.Theme 1.0 as Theme
import "GanttGeometry.js" as Geometry

Item {
    id: root

    property var ganttModel: null
    property int firstRenderedIndex: -1
    property int lastRenderedIndex: -1
    property int rowHeight: 36
    property real verticalContentY: 0
    property int axisStartDay: -1
    property real pixelsPerDay: 0
    property real timelineContentX: 0
    property string selectedTaskId: ""
    property bool dependencyLinesEnabled: true
    property int normalEdgeLimit: 500
    property color normalConnectorColor: Theme.AppTheme.textMuted
    property color selectedConnectorColor: Theme.AppTheme.accent

    readonly property var visibleRoutes: _routes
    readonly property int routeCount: _routes.length
    readonly property int candidateEdgeCount: _candidateEdgeCount
    readonly property bool densitySuppressed: _densitySuppressed
    readonly property int unpositionedEdgeCount: _unpositionedEdgeCount
    readonly property string renderError: _renderError
    readonly property string statusMessage: root._statusMessage()
    readonly property real lastRouteBuildMs: _lastRouteBuildMs
    readonly property real lastPaintMs: dependencyCanvas.lastPaintMs
    readonly property int paintedRouteCount: dependencyCanvas.paintedRouteCount

    property var _routes: []
    property int _candidateEdgeCount: 0
    property bool _densitySuppressed: false
    property int _unpositionedEdgeCount: 0
    property string _renderError: ""
    property real _lastRouteBuildMs: 0
    property bool _rebuildPending: false

    function _statusMessage() {
        if (root._renderError.length > 0)
            return "Dependency lines are unavailable: " + root._renderError
        if (root._densitySuppressed)
            return "Dependency lines limited for performance. Select a task to inspect its links."
        if (root._unpositionedEdgeCount > 0)
            return String(root._unpositionedEdgeCount)
                + " visible dependencies cannot be positioned because endpoint dates are unavailable."
        return ""
    }

    function _scheduleRebuild() {
        root._rebuildPending = true
        paintTimer.restart()
    }

    function _schedulePaint() {
        paintTimer.restart()
    }

    function _invalidateModelRoutes() {
        root._rebuildPending = false
        root._clearRoutes()
        dependencyCanvas.requestPaint()
    }

    function _clearRoutes() {
        root._routes = []
        root._candidateEdgeCount = 0
        root._densitySuppressed = false
        root._unpositionedEdgeCount = 0
        root._renderError = ""
        dependencyCanvas.paintedRouteCount = 0
        dependencyCanvas.lastPaintMs = 0
    }

    function _anchorX(edge, predecessor, finishAnchor) {
        const prefix = predecessor ? "predecessor" : "successor"
        const startDay = edge[prefix + "StartDay"]
        const finishDay = edge[prefix + "FinishDay"]
        if (edge[prefix + "IsMilestone"] === true) {
            return finishAnchor
                ? Geometry.milestoneFinishX(
                    startDay, root.axisStartDay, root.pixelsPerDay
                )
                : Geometry.milestoneStartX(
                    startDay, root.axisStartDay, root.pixelsPerDay
                )
        }
        return finishAnchor
            ? Geometry.taskFinishX(
                startDay,
                finishDay,
                root.axisStartDay,
                root.pixelsPerDay
            )
            : Geometry.dayStartX(startDay, root.axisStartDay, root.pixelsPerDay)
    }

    function _buildRoute(edge) {
        const relation = String(edge.dependencyType || "FS").toUpperCase()
        if (["FS", "SS", "FF", "SF"].indexOf(relation) < 0)
            throw new Error("Unsupported dependency type: " + relation)
        const sourceFinish = relation.charAt(0) === "F"
        const targetFinish = relation.charAt(1) === "F"
        const sourceX = root._anchorX(edge, true, sourceFinish)
        const targetX = root._anchorX(edge, false, targetFinish)
        const sourceY = (Number(edge.predecessorRowIndex) + 0.5) * root.rowHeight
        const targetY = (Number(edge.successorRowIndex) + 0.5) * root.rowHeight
        const gutter = Math.max(8, Math.min(16, root.pixelsPerDay))
        const sourceOuterX = sourceX + (sourceFinish ? gutter : -gutter)
        const targetOuterX = targetX + (targetFinish ? gutter : -gutter)
        let channelX
        if (sourceFinish && !targetFinish && sourceOuterX < targetOuterX)
            channelX = (sourceOuterX + targetOuterX) / 2
        else if (sourceFinish)
            channelX = Math.max(sourceOuterX, targetOuterX) + gutter
        else
            channelX = Math.min(sourceOuterX, targetOuterX) - gutter
        return {
            "dependencyId": String(edge.dependencyId || ""),
            "predecessorTaskId": String(edge.predecessorTaskId || ""),
            "predecessorTaskName": String(edge.predecessorTaskName || ""),
            "successorTaskId": String(edge.successorTaskId || ""),
            "successorTaskName": String(edge.successorTaskName || ""),
            "dependencyType": relation,
            "dependencyTypeLabel": String(edge.dependencyTypeLabel || relation),
            "lagDays": Number(edge.lagDays || 0),
            "predecessorIsCritical": edge.predecessorIsCritical === true,
            "successorIsCritical": edge.successorIsCritical === true,
            "predecessorIsInfeasible": edge.predecessorIsInfeasible === true,
            "successorIsInfeasible": edge.successorIsInfeasible === true,
            "predecessorIsMilestone": edge.predecessorIsMilestone === true,
            "successorIsMilestone": edge.successorIsMilestone === true,
            "selected": edge.selected === true,
            "sourceX": sourceX,
            "sourceY": sourceY,
            "sourceOuterX": sourceOuterX,
            "channelX": channelX,
            "targetOuterX": targetOuterX,
            "targetX": targetX,
            "targetY": targetY,
            "targetFinishAnchor": targetFinish
        }
    }

    function _rebuildRoutes() {
        const started = Date.now()
        if (!root.dependencyLinesEnabled
                || !root.ganttModel
                || root.firstRenderedIndex < 0
                || root.lastRenderedIndex < root.firstRenderedIndex
                || root.axisStartDay < 1
                || root.pixelsPerDay <= 0) {
            root._clearRoutes()
            root._lastRouteBuildMs = Date.now() - started
            return
        }
        try {
            const window = root.ganttModel.dependencyWindow(
                root.firstRenderedIndex,
                root.lastRenderedIndex,
                root.selectedTaskId,
                root.normalEdgeLimit
            )
            const edges = window.edges || []
            const nextRoutes = []
            for (let i = 0; i < edges.length; i++)
                nextRoutes.push(root._buildRoute(edges[i]))
            root._routes = nextRoutes
            root._candidateEdgeCount = Number(window.candidateEdgeCount || 0)
            root._densitySuppressed = window.suppressed === true
            root._unpositionedEdgeCount = Number(window.unpositionedEdgeCount || 0)
            root._renderError = ""
        } catch (error) {
            root._clearRoutes()
            root._renderError = String(error)
        }
        root._lastRouteBuildMs = Date.now() - started
    }

    function _drawArrow(context, route, targetX, targetY) {
        const direction = route.targetFinishAnchor ? -1 : 1
        const baseX = targetX - direction * 7
        context.beginPath()
        context.moveTo(targetX, targetY)
        context.lineTo(baseX, targetY - 4)
        context.lineTo(baseX, targetY + 4)
        context.closePath()
        context.fill()
    }

    Timer {
        id: paintTimer
        interval: 0
        repeat: false

        onTriggered: {
            if (root._rebuildPending) {
                root._rebuildPending = false
                root._rebuildRoutes()
            }
            dependencyCanvas.requestPaint()
        }
    }

    Canvas {
        id: dependencyCanvas
        objectName: "ganttDependencyCanvas"
        anchors.fill: parent
        visible: root.dependencyLinesEnabled && root.routeCount > 0
        renderTarget: Canvas.Image
        renderStrategy: Canvas.Cooperative
        canvasSize: Qt.size(
            Math.max(1, Math.ceil(width * Screen.devicePixelRatio)),
            Math.max(1, Math.ceil(height * Screen.devicePixelRatio))
        )
        property real lastPaintMs: 0
        property int paintedRouteCount: 0

        onPaint: {
            const started = Date.now()
            const context = getContext("2d")
            const dpr = Screen.devicePixelRatio
            context.reset()
            context.scale(dpr, dpr)
            context.lineJoin = "round"
            context.lineCap = "round"
            let painted = 0
            for (let i = 0; i < root._routes.length; i++) {
                const route = root._routes[i]
                const sourceX = route.sourceX - root.timelineContentX
                const sourceOuterX = route.sourceOuterX - root.timelineContentX
                const channelX = route.channelX - root.timelineContentX
                const targetOuterX = route.targetOuterX - root.timelineContentX
                const targetX = route.targetX - root.timelineContentX
                const sourceY = route.sourceY - root.verticalContentY
                const targetY = route.targetY - root.verticalContentY
                context.strokeStyle = route.selected
                    ? root.selectedConnectorColor
                    : root.normalConnectorColor
                context.fillStyle = context.strokeStyle
                context.globalAlpha = route.selected ? 1.0 : 0.72
                context.lineWidth = route.selected ? 2.5 : 1.25
                context.beginPath()
                context.moveTo(sourceX, sourceY)
                context.lineTo(sourceOuterX, sourceY)
                context.lineTo(channelX, sourceY)
                context.lineTo(channelX, targetY)
                context.lineTo(targetOuterX, targetY)
                context.lineTo(targetX, targetY)
                context.stroke()
                root._drawArrow(context, route, targetX, targetY)
                painted += 1
            }
            context.globalAlpha = 1.0
            paintedRouteCount = painted
            lastPaintMs = Date.now() - started
        }

        onWidthChanged: root._schedulePaint()
        onHeightChanged: root._schedulePaint()
        onCanvasSizeChanged: root._schedulePaint()
    }

    onGanttModelChanged: _scheduleRebuild()
    onFirstRenderedIndexChanged: _scheduleRebuild()
    onLastRenderedIndexChanged: _scheduleRebuild()
    onRowHeightChanged: _scheduleRebuild()
    onVerticalContentYChanged: _schedulePaint()
    onAxisStartDayChanged: _scheduleRebuild()
    onPixelsPerDayChanged: _scheduleRebuild()
    onTimelineContentXChanged: _schedulePaint()
    onSelectedTaskIdChanged: _scheduleRebuild()
    onDependencyLinesEnabledChanged: _scheduleRebuild()
    onNormalEdgeLimitChanged: _scheduleRebuild()

    Connections {
        target: root.ganttModel

        function onModelAboutToBeReset() { root._invalidateModelRoutes() }
        function onModelReset() { root._scheduleRebuild() }
        function onProjectionChanged() {
            root._invalidateModelRoutes()
            root._scheduleRebuild()
        }
        function onRowCountChanged() { root._scheduleRebuild() }
    }

    Component.onCompleted: root._scheduleRebuild()
}
