pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import workspaces.scheduling.components 1.0
import "../components/gantt" as Gantt

Item {
    id: root

    property var workspaceController: null
    property var activityColumns: []
    property string activityTableId: "pm.scheduling.activity.table"
    property var selectedActivityModel: ({ "id": "", "title": "", "statusLabel": "", "fields": [] })
    property string ganttViewMode: "split"

    readonly property bool compact: root.width <= Theme.AppTheme.compactContentBreakpoint
    readonly property bool hasSelection: String(root.selectedActivityModel.id || "").length > 0
    readonly property var ganttTimeAxis: root.workspaceController
        ? root.workspaceController.ganttTimeAxis
        : null
    readonly property string effectiveGanttViewMode: ganttSurface.effectiveViewMode
    readonly property int activeGanttDelegateCount: ganttSurface.activeDelegateCount
    readonly property var inspectorSections: (root.selectedActivityModel.fields || []).map(function(field) {
        const supporting = String(field.supportingText || field.supporting_text || "")
        const value = String(field.value || "")
        return {
            "label": String(field.label || ""),
            "value": supporting.length > 0 ? value + " / " + supporting : value
        }
    })
    readonly property var scheduleImpact: root.workspaceController
        ? (root.workspaceController.scheduleImpact || {})
        : ({})
    readonly property bool scheduleImpactAvailable: root.scheduleImpact.available === true
        && String(root.scheduleImpact.taskId || "") === String(root.selectedActivityModel.id || "")

    signal activityColumnsStateChanged(var columns)
    signal activityDetailRequested(string activityId)

    function _buildColumnState(columns) {
        const order = []
        const hidden = []
        for (let i = 0; i < columns.length; i++) {
            order.push(columns[i].key)
            if (columns[i].visible === false) hidden.push(columns[i].key)
        }
        return { "columnOrder": order, "hiddenColumns": hidden }
    }

    function _applyColumnCustomization(draft) {
        const original = {}
        for (let i = 0; i < root.activityColumns.length; i++)
            original[root.activityColumns[i].key] = root.activityColumns[i]
        const next = []
        for (let i = 0; i < draft.length; i++) {
            const source = original[draft[i].key]
            if (!source) continue
            const column = JSON.parse(JSON.stringify(source))
            column.visible = draft[i].visible
            next.push(column)
        }
        for (let i = 0; i < root.activityColumns.length; i++) {
            const source = root.activityColumns[i]
            if (source.configurable === false)
                next.push(JSON.parse(JSON.stringify(source)))
        }
        root.activityColumns = next
        if (root.workspaceController !== null) {
            root.workspaceController.saveTableColumnState(
                root.activityTableId,
                root._buildColumnState(next)
            )
        }
        root.activityColumnsStateChanged(next)
    }

    function _optionIndex(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return list.length > 0 ? 0 : -1
    }

    Component {
        id: inspectorComponent

        AppWidgets.InspectorPanel {
            title: String(root.selectedActivityModel.title || "")
            statusLabel: String(root.selectedActivityModel.statusLabel || "")
            showHeader: !root.compact
            sections: root.inspectorSections
            busy: root.workspaceController ? root.workspaceController.isBusy : false
            editActionLabel: "Open Task"
            showEditAction: true
            showSecondaryAction: false

            onCloseRequested: {
                if (root.workspaceController !== null) root.workspaceController.selectActivity("")
            }
            onEditRequested: root.activityDetailRequested(String(root.selectedActivityModel.id || ""))

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Schedule Impact"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.typeMetadataSize
                    font.bold: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: !root.scheduleImpactAvailable

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: "Not analyzed"
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }

                    AppControls.SecondaryButton {
                        text: "Analyze Impact"
                        enabled: root.workspaceController ? !root.workspaceController.isBusy : false
                        onClicked: {
                            if (root.workspaceController !== null) {
                                root.workspaceController.computeScheduleImpact({
                                    "taskId": root.selectedActivityModel.id
                                })
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.scheduleImpactAvailable
                    spacing: 2

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: String(root.scheduleImpact.summary || "")
                        wrapMode: Text.WordWrap
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }
                    AppControls.Label {
                        text: "Critical path change: " + (root.scheduleImpact.criticalPathChanged ? "Yes" : "No")
                            + " / Conflicts: " + String(root.scheduleImpact.conflictCount || 0)
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }
                    AppControls.Label {
                        text: "Newly critical: " + String(root.scheduleImpact.newlyCriticalCount || 0)
                            + " / No longer critical: " + String(root.scheduleImpact.noLongerCriticalCount || 0)
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }
                    AppControls.Label {
                        visible: Boolean(root.scheduleImpact.requiresApproval)
                        text: "Requires approval before applying."
                        color: Theme.AppTheme.warning
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }
                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: Boolean(root.scheduleImpact.blockedByDeadline)
                        text: String(root.scheduleImpact.blockedReason || "Blocked by a deadline constraint.")
                        wrapMode: Text.WordWrap
                        color: Theme.AppTheme.danger
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }
                }
            }
        }
    }

    SchedulingPanelFrame {
        anchors.fill: parent
        title: "Gantt"
        subtitle: "Integrated work breakdown and current schedule timeline."

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.AppTheme.marginMd
            spacing: Theme.AppTheme.spacingSm

            AppWidgets.TableToolbar {
                id: activityToolbar
                Layout.fillWidth: true
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                searchPlaceholder: "Search activities..."
                showFilter: true
                showCustomize: true
                showExport: false
                showRefresh: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSearchChanged: function(text) {
                    if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                }
                onFilterClicked: activityFilterDialog.open()
                onCustomizeClicked: columnCustomizer.open()
            }

            Flow {
                Layout.fillWidth: true
                Layout.preferredHeight: childrenRect.height
                spacing: Theme.AppTheme.spacingSm

                AppControls.CheckBox {
                    text: "Critical only"
                    checked: root.workspaceController ? root.workspaceController.showCriticalOnly : false
                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                    onToggled: {
                        if (root.workspaceController !== null)
                            root.workspaceController.setShowCriticalOnly(checked)
                    }
                }

                AppControls.CheckBox {
                    text: "Dependency Lines"
                    checked: root.workspaceController
                        ? root.workspaceController.showDependencyLines
                        : true
                    enabled: !(root.workspaceController
                        ? root.workspaceController.isBusy
                        : false)
                    onToggled: {
                        if (root.workspaceController !== null)
                            root.workspaceController.setShowDependencyLines(checked)
                    }
                }

                Row {
                    height: Theme.AppTheme.inputHeight
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Scale"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }

                    AppControls.ComboBox {
                        id: timescaleCombo
                        width: 124
                        model: root.ganttTimeAxis ? root.ganttTimeAxis.timescaleOptions : []
                        textRole: "label"
                        valueRole: "value"
                        searchThreshold: 99
                        enabled: root.ganttTimeAxis ? root.ganttTimeAxis.hasRange : false
                        currentIndex: root._optionIndex(
                            model,
                            root.ganttTimeAxis ? root.ganttTimeAxis.timescale : "week"
                        )
                        onActivated: function(index) {
                            const option = model[index]
                            if (option) ganttSurface.setTimescale(String(option.value || "week"))
                        }
                    }
                }

                Row {
                    height: Theme.AppTheme.toolbarHeight
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.SecondaryButton {
                        width: 44
                        text: "-"
                        enabled: root.ganttTimeAxis ? root.ganttTimeAxis.canZoomOut : false
                        onClicked: ganttSurface.zoomOut()
                        ToolTip.visible: hovered
                        ToolTip.text: "Zoom out"
                    }

                    AppControls.SecondaryButton {
                        width: 68
                        text: root.ganttTimeAxis
                            ? Math.round(root.ganttTimeAxis.zoomMultiplier * 100) + "%"
                            : "100%"
                        enabled: root.ganttTimeAxis ? root.ganttTimeAxis.canResetZoom : false
                        onClicked: ganttSurface.resetZoom()
                        ToolTip.visible: hovered
                        ToolTip.text: "Reset zoom"
                    }

                    AppControls.SecondaryButton {
                        width: 44
                        text: "+"
                        enabled: root.ganttTimeAxis ? root.ganttTimeAxis.canZoomIn : false
                        onClicked: ganttSurface.zoomIn()
                        ToolTip.visible: hovered
                        ToolTip.text: "Zoom in"
                    }
                }

                AppControls.SecondaryButton {
                    width: 84
                    text: "Today"
                    enabled: root.ganttTimeAxis ? root.ganttTimeAxis.todayAvailable : false
                    onClicked: ganttSurface.goToToday()
                    ToolTip.visible: hovered && !enabled
                    ToolTip.text: root.ganttTimeAxis
                        ? root.ganttTimeAxis.todayUnavailableReason
                        : "No scheduled date range is available."
                }

                Row {
                    height: Theme.AppTheme.inputHeight
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "View"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }

                    Repeater {
                        model: ganttSurface.splitAvailable
                            ? [
                                { "id": "grid", "label": "Grid" },
                                { "id": "timeline", "label": "Timeline" },
                                { "id": "split", "label": "Split" }
                            ]
                            : [
                                { "id": "grid", "label": "Grid" },
                                { "id": "timeline", "label": "Timeline" }
                            ]

                        delegate: Rectangle {
                            id: viewModeButton
                            required property var modelData

                            readonly property bool active: root.effectiveGanttViewMode
                                === String(viewModeButton.modelData.id || "")

                            implicitWidth: viewModeLabel.implicitWidth + 18
                            implicitHeight: Theme.AppTheme.inputHeight
                            radius: Theme.AppTheme.radiusSm
                            color: active
                                ? Theme.AppTheme.navSelectedBackground
                                : viewModeHover.hovered
                                    ? Theme.AppTheme.hoverSurface
                                    : Theme.AppTheme.surfaceOverlay
                            border.color: active ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder
                            border.width: active ? 1 : 0

                            AppControls.Label {
                                id: viewModeLabel
                                anchors.centerIn: parent
                                text: String(viewModeButton.modelData.label || "")
                                color: viewModeButton.active
                                    ? Theme.AppTheme.navSelectedText
                                    : Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: viewModeButton.active
                            }

                            HoverHandler { id: viewModeHover; cursorShape: Qt.PointingHandCursor }
                            TapHandler {
                                onTapped: root.ganttViewMode = String(viewModeButton.modelData.id || "grid")
                            }
                        }
                    }
                }
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: ganttSurface.dependencyStatusMessage.length > 0
                text: ganttSurface.dependencyStatusMessage
                wrapMode: Text.WordWrap
                color: ganttSurface.dependencyDensitySuppressed
                    ? Theme.AppTheme.warning
                    : Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.typeSupportingTextSize
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.AppTheme.spacingSm

                Gantt.SchedulingGanttSurface {
                    id: ganttSurface
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    workspaceController: root.workspaceController
                    columns: root.activityColumns
                    requestedViewMode: root.ganttViewMode
                    selectedActivityId: root.workspaceController
                        ? root.workspaceController.selectedActivityId
                        : ""
                    onActivitySelected: function(taskId) {
                        if (root.workspaceController !== null)
                            root.workspaceController.selectActivity(taskId)
                    }
                    onActivityActivated: function(taskId) {
                        if (root.workspaceController !== null)
                            root.workspaceController.selectActivity(taskId)
                        root.activityDetailRequested(taskId)
                    }
                    onSortRequested: function(key, direction) {
                        if (root.workspaceController !== null)
                            root.workspaceController.setActivitySort(key, direction)
                    }
                }

                Loader {
                    Layout.preferredWidth: Theme.AppTheme.inspectorWidth
                    Layout.fillHeight: true
                    active: root.hasSelection && !root.compact
                    visible: active
                    sourceComponent: inspectorComponent
                }
            }
        }
    }

    AppWidgets.TableColumnCustomizer {
        id: columnCustomizer
        columns: root.activityColumns
        onColumnVisibilityChanged: function(columns) {
            root._applyColumnCustomization(columns)
        }
    }

    AppControls.CenteredDialog {
        id: activityFilterDialog

        property string draftStatus: "all"
        property bool draftCriticalOnly: false
        property bool draftDelayedOnly: false

        title: "Filter Activities"
        width: 340
        padding: 0
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        onAboutToShow: {
            draftStatus = root.workspaceController
                ? root.workspaceController.selectedStatusFilter
                : "all"
            draftCriticalOnly = root.workspaceController
                ? root.workspaceController.showCriticalOnly
                : false
            draftDelayedOnly = root.workspaceController
                ? root.workspaceController.showDelayedOnly
                : false
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingMd

            Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.AppTheme.dialogPadding
                Layout.rightMargin: Theme.AppTheme.dialogPadding
                spacing: Theme.AppTheme.spacingSm

                AppControls.Label {
                    text: "Status"
                    font.bold: true
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    color: Theme.AppTheme.textMuted
                }

                AppControls.ComboBox {
                    Layout.fillWidth: true
                    model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                    textRole: "label"
                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                    currentIndex: root._optionIndex(
                        root.workspaceController ? (root.workspaceController.statusOptions || []) : [],
                        activityFilterDialog.draftStatus
                    )
                    onActivated: function(index) {
                        const options = root.workspaceController
                            ? (root.workspaceController.statusOptions || [])
                            : []
                        if (options[index])
                            activityFilterDialog.draftStatus = String(options[index].value || "all")
                    }
                }

                AppControls.CheckBox {
                    text: "Critical only"
                    checked: activityFilterDialog.draftCriticalOnly
                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                    onToggled: activityFilterDialog.draftCriticalOnly = checked
                }

                AppControls.CheckBox {
                    text: "Delayed only"
                    checked: activityFilterDialog.draftDelayedOnly
                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                    onToggled: activityFilterDialog.draftDelayedOnly = checked
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: Theme.AppTheme.divider
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: Theme.AppTheme.dialogPadding
                Layout.rightMargin: Theme.AppTheme.dialogPadding
                Layout.bottomMargin: Theme.AppTheme.spacingSm
                spacing: Theme.AppTheme.spacingSm

                AppControls.SecondaryButton {
                    text: "Clear"
                    iconName: "refresh"
                    onClicked: {
                        if (root.workspaceController !== null)
                            root.workspaceController.clearFilters()
                        activityFilterDialog.close()
                    }
                }

                Item { Layout.fillWidth: true }

                AppControls.PrimaryButton {
                    text: "Apply"
                    iconName: "approve"
                    onClicked: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setStatusFilter(activityFilterDialog.draftStatus)
                            root.workspaceController.setShowCriticalOnly(activityFilterDialog.draftCriticalOnly)
                            root.workspaceController.setShowDelayedOnly(activityFilterDialog.draftDelayedOnly)
                        }
                        activityFilterDialog.close()
                    }
                }
            }
        }
    }

    AppWidgets.SlideOverPanel {
        anchors.fill: parent
        open: root.hasSelection && root.compact
        panelWidth: Math.min(360, Math.max(240, root.width - 80))
        title: String(root.selectedActivityModel.title || "")
        onCloseRequested: {
            if (root.workspaceController !== null) root.workspaceController.selectActivity("")
        }

        Loader {
            anchors.fill: parent
            active: root.hasSelection && root.compact
            sourceComponent: inspectorComponent
        }
    }
}
