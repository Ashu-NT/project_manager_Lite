pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import workspaces.scheduling.components 1.0

Item {
    id: root

    property var workspaceController: null
    property var activityColumns: []
    property string activityTableId: "pm.scheduling.activity.table"
    property var timelineModel: ({ "title": "", "subtitle": "", "items": [], "emptyState": "" })
    property var selectedActivityModel: ({ "id": "", "title": "", "statusLabel": "", "fields": [] })
    property var shellModel: null

    // "split" | "grid" | "timeline" -- a Gantt-local view-mode control, not
    // navigation. "split" is unavailable at compact widths (see
    // _effectiveViewMode) since a fixed grid+timeline split doesn't fit.
    property string ganttViewMode: "split"

    signal activityColumnsStateChanged(var cols)

    readonly property bool _compact: root.width < Theme.AppTheme.compactContentBreakpoint
    // Split mode needs both SplitView panes' minimum widths (420 + 360) plus
    // the inline inspector column whenever a task is selected -- at exactly
    // the compact breakpoint that combination (1068px) can exceed the
    // available width even though _compact alone is false, so fall back to
    // "grid" in that case too rather than only checking _compact.
    readonly property bool _splitFitsWithInspector: !root._hasSelection
        || (root.width - Theme.AppTheme.inspectorWidth) >= 780
    readonly property string _effectiveViewMode: (root.ganttViewMode === "split"
            && (root._compact || !root._splitFitsWithInspector))
        ? "grid"
        : root.ganttViewMode
    readonly property bool _hasSelection: String(root.selectedActivityModel.id || "").length > 0
    readonly property var _inspectorSections: (root.selectedActivityModel.fields || []).map(function(field) {
        const supporting = String(field.supportingText || field.supporting_text || "")
        const value = String(field.value || "")
        return {
            "label": String(field.label || ""),
            "value": supporting.length > 0 ? (value + " · " + supporting) : value
        }
    })
    readonly property var _scheduleImpact: root.workspaceController ? (root.workspaceController.scheduleImpact || {}) : ({})
    readonly property bool _scheduleImpactAvailable: root._scheduleImpact.available === true
        && String(root._scheduleImpact.taskId || "") === String(root.selectedActivityModel.id || "")

    function _buildColumnState(columns) {
        const order = []
        const hidden = []
        for (let i = 0; i < columns.length; i++) {
            order.push(columns[i].key)
            if (columns[i].visible === false) hidden.push(columns[i].key)
        }
        return { "columnOrder": order, "hiddenColumns": hidden }
    }

    function _optionIndex(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return list.length > 0 ? 0 : -1
    }

    // Shared Inspector content -- instantiated inline at wide widths and
    // inside a SlideOverPanel at compact widths (below), so the facts,
    // "Open Task" action, and lazy Schedule Impact block are defined once.
    Component {
        id: _inspectorComponent

        AppWidgets.InspectorPanel {
            title: String(root.selectedActivityModel.title || "")
            statusLabel: String(root.selectedActivityModel.statusLabel || "")
            sections: root._inspectorSections
            busy: root.workspaceController ? root.workspaceController.isBusy : false
            editActionLabel: "Open Task"
            showEditAction: true
            showSecondaryAction: false

            onCloseRequested: {
                if (root.workspaceController !== null) root.workspaceController.selectActivity("")
            }
            onEditRequested: {
                if (root.shellModel) root.shellModel.selectRoute("project_management.tasks")
            }

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
                    visible: !root._scheduleImpactAvailable

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
                            if (root.workspaceController !== null)
                                root.workspaceController.computeScheduleImpact({
                                    "taskId": root.selectedActivityModel.id
                                })
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root._scheduleImpactAvailable
                    spacing: 2

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: String(root._scheduleImpact.summary || "")
                        wrapMode: Text.WordWrap
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }
                    AppControls.Label {
                        text: "Critical path change: " + (root._scheduleImpact.criticalPathChanged ? "Yes" : "No")
                            + " · Conflicts: " + String(root._scheduleImpact.conflictCount || 0)
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }
                    AppControls.Label {
                        text: "Newly critical: " + String(root._scheduleImpact.newlyCriticalCount || 0)
                            + " · No longer critical: " + String(root._scheduleImpact.noLongerCriticalCount || 0)
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }
                    AppControls.Label {
                        visible: Boolean(root._scheduleImpact.requiresApproval)
                        text: "Requires approval before applying."
                        color: Theme.AppTheme.warning
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }
                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: Boolean(root._scheduleImpact.blockedByDeadline)
                        text: String(root._scheduleImpact.blockedReason || "Blocked by a deadline constraint.")
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
        subtitle: "Primary planning console with filtered activities and the current schedule timeline."

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
                onFilterClicked: activityFilterPopup.open()
                onCustomizeClicked: activityTable.openColumnCustomizer(activityToolbar.customizeButtonItem)
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.CheckBox {
                    text: "Critical Path"
                    checked: root.workspaceController ? root.workspaceController.showCriticalOnly : false
                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                    onToggled: {
                        if (root.workspaceController !== null) root.workspaceController.setShowCriticalOnly(checked)
                    }
                }

                Item { Layout.fillWidth: true }

                AppControls.Label {
                    text: "View:"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }

                Repeater {
                    model: root._compact
                        ? [ { "id": "grid", "label": "Grid" }, { "id": "timeline", "label": "Timeline" } ]
                        : [ { "id": "grid", "label": "Grid" }, { "id": "timeline", "label": "Timeline" }, { "id": "split", "label": "Split" } ]

                    delegate: Rectangle {
                        id: viewModeButton
                        required property var modelData

                        readonly property bool _active: root._effectiveViewMode === String(modelData.id || "")

                        implicitWidth: _label.implicitWidth + 18
                        implicitHeight: Theme.AppTheme.inputHeight
                        radius: Theme.AppTheme.radiusSm
                        color: viewModeButton._active
                            ? Theme.AppTheme.navSelectedBackground
                            : _hover.containsMouse
                                ? Theme.AppTheme.hoverSurface
                                : Theme.AppTheme.surfaceOverlay
                        border.color: viewModeButton._active ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder
                        border.width: viewModeButton._active ? 1 : 0

                        AppControls.Label {
                            id: _label
                            anchors.centerIn: parent
                            text: String(viewModeButton.modelData.label || "")
                            color: viewModeButton._active ? Theme.AppTheme.navSelectedText : Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: viewModeButton._active
                        }

                        MouseArea {
                            id: _hover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.ganttViewMode = String(viewModeButton.modelData.id || "")
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Theme.AppTheme.spacingSm

                SplitView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    orientation: Qt.Horizontal

                    Item {
                        SplitView.minimumWidth: 420
                        SplitView.preferredWidth: 640
                        SplitView.fillWidth: root._effectiveViewMode !== "timeline"
                        SplitView.fillHeight: true
                        visible: root._effectiveViewMode !== "timeline"

                        AppWidgets.DataTable {
                            id: activityTable
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: activityPagination.top
                            tableId: root.activityTableId
                            columns: root.activityColumns
                            sourceModel: root.workspaceController ? root.workspaceController.scheduleTableModel : null
                            sortingMode: "server"
                            sortKey: root.workspaceController ? root.workspaceController.activitySortKey : "schedule"
                            sortDirection: root.workspaceController
                                ? root.workspaceController.activitySortDirection
                                : Qt.AscendingOrder
                            loading: root.workspaceController ? root.workspaceController.isLoading : false
                            emptyText: root.workspaceController ? (root.workspaceController.schedule.emptyState || "No activities are available for the selected planning scope.") : "No activities are available."
                            selectedRowId: root.workspaceController ? root.workspaceController.selectedActivityId : ""
                            onColumnsStateChanged: function(cols) {
                                if (root.workspaceController)
                                    root.workspaceController.saveTableColumnState(root.activityTableId, root._buildColumnState(cols))
                                root.activityColumnsStateChanged(cols)
                            }
                            onSortRequested: function(key, direction) {
                                if (root.workspaceController !== null)
                                    root.workspaceController.setActivitySort(key, direction)
                            }
                            onRowSelected: function(rowId) {
                                if (root.workspaceController !== null) root.workspaceController.selectActivity(rowId)
                            }
                        }

                        AppWidgets.TablePaginationBar {
                            id: activityPagination
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            currentPage: root.workspaceController ? root.workspaceController.activityPage : 1
                            pageSize: root.workspaceController ? root.workspaceController.activityPageSize : 25
                            totalItems: root.workspaceController ? root.workspaceController.activityTotalCount : 0
                            busy: root.workspaceController ? root.workspaceController.isBusy : false
                            onPageRequested: function(page) {
                                if (root.workspaceController !== null) root.workspaceController.setActivityPage(page)
                            }
                            onPageSizeRequested: function(pageSize) {
                                if (root.workspaceController !== null) root.workspaceController.setActivityPageSize(pageSize)
                            }
                        }

                        AppControls.CenteredDialog {
                            id: activityFilterPopup

                            // Draft selections, staged until Apply commits them.
                            property string _draftStatus: "all"
                            property bool _draftCriticalOnly: false
                            property bool _draftDelayedOnly: false

                            title: "Filter Activities"
                            width: 340
                            padding: 0
                            modal: true
                            focus: true
                            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                            onAboutToShow: {
                                _draftStatus = root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                                _draftCriticalOnly = root.workspaceController ? root.workspaceController.showCriticalOnly : false
                                _draftDelayedOnly = root.workspaceController ? root.workspaceController.showDelayedOnly : false
                            }

                            contentItem: ColumnLayout {
                                spacing: Theme.AppTheme.spacingMd

                                Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: Theme.AppTheme.dialogPadding
                                    Layout.rightMargin: Theme.AppTheme.dialogPadding
                                    spacing: Theme.AppTheme.spacingSm

                                    AppControls.Label { text: "Status"; font.bold: true; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; color: Theme.AppTheme.textMuted }

                                    AppControls.ComboBox {
                                        Layout.fillWidth: true
                                        model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                        textRole: "label"
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                        currentIndex: root._optionIndex(
                                            root.workspaceController ? (root.workspaceController.statusOptions || []) : [],
                                            activityFilterPopup._draftStatus
                                        )
                                        onActivated: function(index) {
                                            const options = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                            if (options[index])
                                                activityFilterPopup._draftStatus = String(options[index].value || "all")
                                        }
                                    }

                                    AppControls.CheckBox {
                                        text: "Critical only"
                                        checked: activityFilterPopup._draftCriticalOnly
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                        onToggled: activityFilterPopup._draftCriticalOnly = checked
                                    }

                                    AppControls.CheckBox {
                                        text: "Delayed only"
                                        checked: activityFilterPopup._draftDelayedOnly
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                        onToggled: activityFilterPopup._draftDelayedOnly = checked
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
                                            if (root.workspaceController !== null) root.workspaceController.clearFilters()
                                            activityFilterPopup.close()
                                        }
                                    }

                                    Item { Layout.fillWidth: true }

                                    AppControls.PrimaryButton {
                                        text: "Apply"
                                        iconName: "approve"
                                        onClicked: {
                                            if (root.workspaceController !== null) {
                                                root.workspaceController.setStatusFilter(activityFilterPopup._draftStatus)
                                                root.workspaceController.setShowCriticalOnly(activityFilterPopup._draftCriticalOnly)
                                                root.workspaceController.setShowDelayedOnly(activityFilterPopup._draftDelayedOnly)
                                            }
                                            activityFilterPopup.close()
                                        }
                                    }
                                }
                            }
                        }
                    }

                    SchedulingTimelinePanel {
                        SplitView.minimumWidth: 360
                        SplitView.preferredWidth: 480
                        SplitView.fillWidth: root._effectiveViewMode === "timeline"
                        SplitView.fillHeight: true
                        visible: root._effectiveViewMode !== "grid"
                        timelineModel: root.timelineModel
                        selectedActivityId: root.workspaceController ? root.workspaceController.selectedActivityId : ""
                        onActivitySelected: function(activityId) {
                            if (root.workspaceController !== null) root.workspaceController.selectActivity(activityId)
                        }
                    }
                }

                Loader {
                    Layout.preferredWidth: Theme.AppTheme.inspectorWidth
                    Layout.fillHeight: true
                    active: root._hasSelection && !root._compact
                    visible: active
                    sourceComponent: _inspectorComponent
                }
            }
        }
    }

    AppWidgets.SlideOverPanel {
        anchors.fill: parent
        open: root._hasSelection && root._compact
        panelWidth: Math.min(360, Math.max(240, root.width - 80))
        title: String(root.selectedActivityModel.title || "")
        onCloseRequested: {
            if (root.workspaceController !== null) root.workspaceController.selectActivity("")
        }

        Loader {
            anchors.fill: parent
            active: root._hasSelection && root._compact
            sourceComponent: _inspectorComponent
        }
    }
}
