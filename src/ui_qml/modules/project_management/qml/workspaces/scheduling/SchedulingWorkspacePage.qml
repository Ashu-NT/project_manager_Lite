pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementSchedulingWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.schedulingWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.scheduling",
            "title": "Scheduling",
            "summary": "Enterprise planning console for CPM schedule control, baselines, and resource pressure.",
            "migrationStatus": "QML scheduling operations slice active",
            "legacyRuntimeStatus": "QML runtime is active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var scheduleModel: root.workspaceController
        ? root.workspaceController.schedule
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "Scheduling desktop API is not connected." })
    readonly property var timelineModel: root.workspaceController
        ? root.workspaceController.timeline
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No timeline is available." })
    readonly property var diagnosticsModel: root.workspaceController
        ? root.workspaceController.diagnostics
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "" })
    readonly property var criticalPathModel: root.workspaceController
        ? root.workspaceController.criticalPath
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "" })
    readonly property var delayedActivitiesModel: root.workspaceController
        ? root.workspaceController.delayedActivities
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "" })
    readonly property var resourceLoadingModel: root.workspaceController
        ? root.workspaceController.resourceLoading
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "" })
    readonly property var baselineRegisterModel: root.workspaceController
        ? root.workspaceController.baselineRegister
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "" })
    readonly property var baselinesModel: root.workspaceController
        ? root.workspaceController.baselines
        : ({ "options": [], "rows": [], "summaryText": "", "emptyState": "" })
    readonly property var selectedActivityModel: root.workspaceController
        ? root.workspaceController.selectedActivity
        : ({ "id": "", "title": "", "subtitle": "", "description": "", "fields": [], "state": {}, "emptyState": "Select an activity to inspect schedule details." })
    readonly property var dependenciesModel: root.workspaceController
        ? root.workspaceController.dependencies
        : ({ "items": [], "emptyState": "" })
    readonly property var constraintsModel: root.workspaceController
        ? root.workspaceController.constraints
        : ({ "items": [], "emptyState": "" })
    readonly property var calendarModel: root.workspaceController
        ? root.workspaceController.calendar
        : ({ "summaryText": "", "workingDays": [], "hoursPerDay": "8", "holidays": [], "emptyState": "" })
    readonly property var activityFeedModel: root.workspaceController
        ? root.workspaceController.activityFeed
        : ({ "items": [], "emptyState": "" })

    property string selectedBaselineRegisterId: ""

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    readonly property var _activityColumns: [
        { "key": "activityId", "label": "Activity ID", "flex": 0, "minWidth": 96, "sortable": true },
        { "key": "wbs", "label": "WBS", "flex": 0, "minWidth": 78, "sortable": true },
        { "key": "taskName", "label": "Task Name", "flex": 2.1, "sortable": true },
        { "key": "start", "label": "Start", "flex": 0, "minWidth": 96, "sortable": true },
        { "key": "finish", "label": "Finish", "flex": 0, "minWidth": 96, "sortable": true },
        { "key": "duration", "label": "Duration", "flex": 0, "minWidth": 84 },
        { "key": "remainingDuration", "label": "Remaining", "flex": 0, "minWidth": 96 },
        { "key": "float", "label": "Float", "flex": 0, "minWidth": 72 },
        { "key": "critical", "label": "Critical", "flex": 0, "minWidth": 86, "type": "status" },
        { "key": "constraint", "label": "Constraint", "flex": 1.0 },
        { "key": "calendar", "label": "Calendar", "flex": 1.0 },
        { "key": "progress", "label": "Progress", "flex": 1.0, "minWidth": 120, "type": "progress" },
        { "key": "status", "label": "Status", "flex": 0, "minWidth": 96, "type": "status" }
    ]
    readonly property var _diagnosticColumns: [
        { "key": "check", "label": "Check", "flex": 1.2 },
        { "key": "value", "label": "Value", "flex": 0.5 },
        { "key": "detail", "label": "Detail", "flex": 1.6 },
        { "key": "status", "label": "Status", "flex": 0.8, "type": "status" }
    ]
    readonly property var _criticalColumns: [
        { "key": "activity", "label": "Critical Activity", "flex": 1.5 },
        { "key": "window", "label": "Window", "flex": 1.0 },
        { "key": "float", "label": "Float", "flex": 0.6 },
        { "key": "progress", "label": "Progress", "flex": 1.0, "type": "progress" }
    ]
    readonly property var _baselineCompareColumns: [
        { "key": "activity", "label": "Activity", "flex": 1.4 },
        { "key": "change", "label": "Change", "flex": 0.8, "type": "status" },
        { "key": "shift", "label": "Shift", "flex": 1.4 },
        { "key": "dates", "label": "Baseline Dates", "flex": 2.0 },
        { "key": "cost", "label": "Cost Delta", "flex": 1.0 }
    ]
    readonly property var _baselineRegisterColumns: [
        { "key": "baseline", "label": "Baseline", "flex": 1.4 },
        { "key": "created", "label": "Created", "flex": 1.0 },
        { "key": "approvedBy", "label": "Approved By", "flex": 1.0 },
        { "key": "state", "label": "State", "flex": 0.8, "type": "status" }
    ]
    readonly property var _resourceColumns: [
        { "key": "resource", "label": "Resource", "flex": 1.3 },
        { "key": "allocation", "label": "Allocation", "flex": 0.8 },
        { "key": "capacity", "label": "Capacity", "flex": 0.8 },
        { "key": "utilization", "label": "Utilization", "flex": 0.8 },
        { "key": "tasks", "label": "Tasks", "flex": 0.5 },
        { "key": "status", "label": "Status", "flex": 0.8, "type": "status" }
    ]
    readonly property var _delayedColumns: [
        { "key": "activity", "label": "Delayed Activity", "flex": 1.5 },
        { "key": "finish", "label": "Finish", "flex": 0.8 },
        { "key": "deadline", "label": "Deadline", "flex": 0.8 },
        { "key": "delay", "label": "Delay", "flex": 0.7 },
        { "key": "status", "label": "Status", "flex": 0.8, "type": "status" }
    ]

    readonly property var _detailActions: [
        { "id": "add_dependency", "label": "Add Dependency", "icon": "add", "enabled": true, "danger": false },
        { "id": "save_baseline", "label": "Save Baseline", "icon": "register", "enabled": true, "danger": false },
        { "id": "recalculate", "label": "Recalculate", "icon": "refresh", "enabled": true, "danger": false }
    ]

    function _optionIndex(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) {
                return i
            }
        }
        return optionList.length > 0 ? 0 : -1
    }

    function _scheduleRows() {
        const items = root.scheduleModel.items || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "activityId": String(state.activityCode || item.id || ""),
                "wbs": String(state.wbs || ""),
                "taskName": item.title,
                "start": String(state.startDateLabel || ""),
                "finish": String(state.finishDateLabel || ""),
                "duration": String(state.durationLabel || ""),
                "remainingDuration": String(state.remainingDurationLabel || ""),
                "float": String(state.floatLabel || ""),
                "critical": String(state.criticalLabel || ""),
                "constraint": String(state.constraintLabel || ""),
                "calendar": String(state.calendarLabel || ""),
                "progress": state.progressValue || { "value": 0, "label": "0%" },
                "status": item.statusLabel
            })
        }
        return rows
    }

    function _diagnosticRows() {
        const items = root.diagnosticsModel.items || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            rows.push({
                "id": item.id,
                "check": item.title,
                "value": item.subtitle,
                "detail": item.supportingText,
                "status": item.statusLabel
            })
        }
        return rows
    }

    function _criticalRows() {
        const items = root.criticalPathModel.items || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            const progressMatch = String(item.supportingText || "").match(/Progress\s+(\d+%?)/)
            const progressLabel = progressMatch && progressMatch.length > 1 ? progressMatch[1] : "0%"
            const progressNumber = parseInt(progressLabel, 10) || 0
            rows.push({
                "id": item.id,
                "activity": item.title,
                "window": item.subtitle,
                "float": String((item.supportingText || "").split("|")[0] || ""),
                "progress": {
                    "value": Math.max(0, Math.min(1, progressNumber / 100)),
                    "label": progressLabel
                }
            })
        }
        return rows
    }

    function _baselineCompareRows() {
        const items = root.baselinesModel.rows || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            rows.push({
                "id": item.id,
                "activity": item.title,
                "change": item.statusLabel,
                "shift": item.supportingText,
                "dates": item.subtitle,
                "cost": item.metaText
            })
        }
        return rows
    }

    function _baselineRegisterRows() {
        const items = root.baselineRegisterModel.items || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "baseline": item.title,
                "created": String(state.createdLabel || item.subtitle || ""),
                "approvedBy": String(state.approvedByLabel || ""),
                "state": String(state.varianceState || item.statusLabel || "")
            })
        }
        return rows
    }

    function _resourceRows() {
        const items = root.resourceLoadingModel.items || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            const state = item.state || {}
            rows.push({
                "id": item.id,
                "resource": item.title,
                "allocation": String(state.allocationLabel || ""),
                "capacity": String(state.capacityLabel || ""),
                "utilization": String(state.utilizationLabel || ""),
                "tasks": String(state.tasksCount || ""),
                "status": item.statusLabel
            })
        }
        return rows
    }

    function _delayedRows() {
        const items = root.delayedActivitiesModel.items || []
        const rows = []
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i]
            const subtitle = String(item.subtitle || "")
            const parts = subtitle.split("|")
            rows.push({
                "id": item.id,
                "activity": item.title,
                "finish": parts.length > 0 ? String(parts[0]).replace("Finish ", "").trim() : "",
                "deadline": parts.length > 1 ? String(parts[1]).replace("Deadline ", "").trim() : "",
                "delay": item.supportingText,
                "status": item.statusLabel
            })
        }
        return rows
    }

    SchedulingDialogHost {
        id: dialogHost

        selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
        selectedActivityData: root.selectedActivityModel
        dependencyTypeOptions: root.workspaceController ? (root.workspaceController.dependencyTypeOptions || []) : []
        dependencyTaskOptions: root.workspaceController ? (root.workspaceController.dependencyTaskOptions || []) : []

        onCreateBaselineRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createBaseline(payload)
            }
        }
        onCreateDependencyRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createDependency(payload)
            }
        }
        onUpdateDependencyRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateDependency(payload)
            }
        }
        onDeleteDependencyRequested: function(dependencyId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteDependency(dependencyId)
            }
        }
    }

    Item {
        anchors.fill: parent

        Item {
            id: listPage
            anchors.fill: parent
            visible: !detailPage.open

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                SchedulingPlanningToolbar {
                    id: planningToolbar
                    Layout.fillWidth: true
                    projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                    baselineOptions: root.workspaceController ? (root.workspaceController.baselineOptions || []) : []
                    calendarOptions: root.workspaceController ? (root.workspaceController.calendarOptions || []) : []
                    selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                    selectedBaselineId: root.workspaceController ? root.workspaceController.selectedBaselineId : ""
                    selectedCalendarId: root.workspaceController ? root.workspaceController.selectedCalendarId : "default"
                    searchText: root.workspaceController ? root.workspaceController.searchText : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onProjectSelected: function(projectId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectProject(projectId)
                        }
                    }
                    onBaselineSelected: function(baselineId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectBaseline(baselineId)
                        }
                    }
                    onCalendarSelected: function(calendarId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectCalendar(calendarId)
                        }
                    }
                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setSearchText(text)
                        }
                    }
                    onFilterRequested: filterPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.refresh()
                        }
                    }
                    onSaveBaselineRequested: dialogHost.openCreateBaselineDialog()
                    onRecalculateRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.recalculateSchedule()
                        }
                    }
                    onExportRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.exportSchedule()
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                        && !(root.workspaceController ? root.workspaceController.isBusy : false)
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "info"
                    message: "Loading enterprise planning data..."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.workspaceController
                        ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    tone: "info"
                    message: "Applying planning changes..."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root.overviewModel.metrics || []
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: Math.max(340, root.height * 0.5)
                    spacing: Theme.AppTheme.spacingSm

                    SchedulingPanelFrame {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: root.width * 0.64
                        title: "Schedule Activities"
                        subtitle: "Current activities, CPM timing, float, constraints, and status control."

                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            AppWidgets.DataTable {
                                id: activitiesTable
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: activityPagination.top
                                columns: root._activityColumns
                                rows: root._scheduleRows()
                                loading: root.workspaceController ? root.workspaceController.isLoading : false
                                emptyText: root.scheduleModel.emptyState || "No scheduled activities are available."
                                selectedRowId: root.workspaceController ? root.workspaceController.selectedActivityId : ""

                                onRowSelected: function(rowId) {
                                    if (root.workspaceController !== null) {
                                        root.workspaceController.selectActivity(rowId)
                                    }
                                }
                                onRowActivated: function(rowId) {
                                    if (root.workspaceController !== null) {
                                        root.workspaceController.activateActivity(rowId)
                                    }
                                    detailPage.open = true
                                }
                                onSortRequested: function(key) {}
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
                                    if (root.workspaceController !== null) {
                                        root.workspaceController.setActivityPage(page)
                                    }
                                }
                                onPageSizeRequested: function(pageSize) {
                                    if (root.workspaceController !== null) {
                                        root.workspaceController.setActivityPageSize(pageSize)
                                    }
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: root.width * 0.36
                        spacing: Theme.AppTheme.spacingSm

                        SchedulingTimelinePanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredHeight: 280
                            timelineModel: root.timelineModel
                        }

                        SchedulingPanelFrame {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Diagnostics"
                            subtitle: "Network health checks and critical-path watch."

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: Theme.AppTheme.spacingSm

                                AppWidgets.DataTable {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    columns: root._diagnosticColumns
                                    rows: root._diagnosticRows()
                                    emptyText: root.diagnosticsModel.emptyState || "No diagnostics are available."
                                    loading: false
                                }

                                AppWidgets.DataTable {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    columns: root._criticalColumns
                                    rows: root._criticalRows()
                                    emptyText: root.criticalPathModel.emptyState || "No critical-path activities are visible."
                                    loading: false
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.max(240, root.height * 0.28)
                    spacing: Theme.AppTheme.spacingSm

                    SchedulingPanelFrame {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: root.width * 0.42
                        title: "Baselines"
                        subtitle: "Variance comparison and baseline register."

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: Theme.AppTheme.spacingSm

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                ComboBox {
                                    Layout.preferredWidth: 200
                                    model: root.baselinesModel.options || []
                                    textRole: "label"
                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                    currentIndex: root._optionIndex(root.baselinesModel.options || [], root.baselinesModel.selectedBaselineAId || "")
                                    onActivated: function(index) {
                                        const option = (root.baselinesModel.options || [])[index]
                                        if (option && root.workspaceController !== null) {
                                            root.workspaceController.selectBaselineA(String(option.value || ""))
                                        }
                                    }
                                }

                                ComboBox {
                                    Layout.preferredWidth: 200
                                    model: root.baselinesModel.options || []
                                    textRole: "label"
                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                    currentIndex: root._optionIndex(root.baselinesModel.options || [], root.baselinesModel.selectedBaselineBId || "")
                                    onActivated: function(index) {
                                        const option = (root.baselinesModel.options || [])[index]
                                        if (option && root.workspaceController !== null) {
                                            root.workspaceController.selectBaselineB(String(option.value || ""))
                                        }
                                    }
                                }

                                CheckBox {
                                    text: "Include unchanged"
                                    checked: Boolean(root.baselinesModel.includeUnchanged)
                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                    onToggled: {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.setIncludeUnchanged(checked)
                                        }
                                    }
                                }

                                Item { Layout.fillWidth: true }
                            }

                            AppWidgets.InlineMessage {
                                Layout.fillWidth: true
                                tone: "info"
                                message: root.baselinesModel.summaryText || root.baselinesModel.emptyState || ""
                            }

                            AppWidgets.DataTable {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 130
                                columns: root._baselineCompareColumns
                                rows: root._baselineCompareRows()
                                emptyText: root.baselinesModel.emptyState || "Choose two baselines to compare."
                                loading: false
                            }

                            AppWidgets.DataTable {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                columns: root._baselineRegisterColumns
                                rows: root._baselineRegisterRows()
                                selectedRowId: root.selectedBaselineRegisterId
                                emptyText: root.baselineRegisterModel.emptyState || "No baselines are stored."
                                loading: false

                                onRowSelected: function(rowId) {
                                    root.selectedBaselineRegisterId = String(rowId || "")
                                }
                            }
                        }
                    }

                    SchedulingPanelFrame {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: root.width * 0.28
                        title: "Resource Loading"
                        subtitle: "Capacity, utilization, and overload watch."

                        AppWidgets.DataTable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            columns: root._resourceColumns
                            rows: root._resourceRows()
                            emptyText: root.resourceLoadingModel.emptyState || "No resource load data is available."
                            loading: false
                        }
                    }

                    SchedulingPanelFrame {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.preferredWidth: root.width * 0.30
                        title: "Delayed Activities"
                        subtitle: "Activities already beyond their current deadline protection."

                        AppWidgets.DataTable {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            columns: root._delayedColumns
                            rows: root._delayedRows()
                            emptyText: root.delayedActivitiesModel.emptyState || "No delayed activities are visible."
                            loading: false
                        }
                    }
                }
            }

            Popup {
                id: filterPopup
                parent: planningToolbar
                width: 280
                padding: Theme.AppTheme.marginMd
                x: planningToolbar.width - width
                y: planningToolbar.height + Theme.AppTheme.spacingXs
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                background: Rectangle {
                    radius: Theme.AppTheme.radiusLg
                    color: Theme.AppTheme.surfaceRaised
                    border.color: Theme.AppTheme.divider
                    border.width: 1
                }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm

                    Label {
                        text: "Status"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }

                    ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndex(
                            root.workspaceController ? (root.workspaceController.statusOptions || []) : [],
                            root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                        )
                        onActivated: function(index) {
                            const options = root.workspaceController
                                ? (root.workspaceController.statusOptions || [])
                                : []
                            if (root.workspaceController !== null && options[index]) {
                                root.workspaceController.setStatusFilter(String(options[index].value || "all"))
                            }
                        }
                    }

                    CheckBox {
                        text: "Critical path only"
                        checked: root.workspaceController ? root.workspaceController.showCriticalOnly : false
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onToggled: {
                            if (root.workspaceController !== null) {
                                root.workspaceController.setShowCriticalOnly(checked)
                            }
                        }
                    }

                    CheckBox {
                        text: "Delayed activities only"
                        checked: root.workspaceController ? root.workspaceController.showDelayedOnly : false
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onToggled: {
                            if (root.workspaceController !== null) {
                                root.workspaceController.setShowDelayedOnly(checked)
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.SecondaryButton {
                            Layout.fillWidth: true
                            text: "Clear"
                            iconName: "close"
                            onClicked: {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.clearFilters()
                                }
                                filterPopup.close()
                            }
                        }

                        AppControls.SecondaryButton {
                            Layout.fillWidth: true
                            text: "Close"
                            iconName: "approve"
                            onClicked: filterPopup.close()
                        }
                    }
                }
            }
        }

        AppWidgets.SectionDetailPage {
            id: detailPage
            anchors.fill: parent
            open: false
            showHeader: false
            showEdit: false
            showDelete: false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
            sections: [
                "Activity Details",
                { "label": "Dependencies", "count": (root.dependenciesModel.items || []).length },
                { "label": "Constraints", "count": (root.constraintsModel.items || []).length },
                { "label": "Calendars", "count": (root.calendarModel.holidays || []).length },
                { "label": "Baselines", "count": (root.baselineRegisterModel.items || []).length },
                { "label": "Resources", "count": (root.resourceLoadingModel.items || []).length },
                { "label": "Activity", "count": (root.activityFeedModel.items || []).length }
            ]
            z: 20

            AppWidgets.ContextualActionToolbar {
                width: parent ? parent.width : 0
                showBack: true
                title: root.selectedActivityModel.title || "Activity Details"
                subtitle: root.selectedActivityModel.statusLabel || root.selectedActivityModel.subtitle || ""
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: root._detailActions

                onBackRequested: detailPage.open = false
                onActionTriggered: function(actionId) {
                    if (actionId === "add_dependency") {
                        dialogHost.openCreateDependencyDialog(root.selectedActivityModel)
                    } else if (actionId === "save_baseline") {
                        dialogHost.openCreateBaselineDialog()
                    } else if (actionId === "recalculate") {
                        if (root.workspaceController !== null) {
                            root.workspaceController.recalculateSchedule()
                        }
                    }
                }
            }

            SchedulingDetailPanel {
                width: parent ? parent.width : 0
                detailPage: detailPage
                activityDetail: root.selectedActivityModel
                dependenciesModel: root.dependenciesModel
                constraintsModel: root.constraintsModel
                calendarModel: root.calendarModel
                baselinesModel: root.baselinesModel
                baselineRegisterModel: root.baselineRegisterModel
                resourceLoadingModel: root.resourceLoadingModel
                activityFeedModel: root.activityFeedModel
                calculatorResult: root.workspaceController ? root.workspaceController.calculatorResult : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onCreateDependencyRequested: dialogHost.openCreateDependencyDialog(root.selectedActivityModel)
                onEditDependencyRequested: function(dependencyData) {
                    dialogHost.openEditDependencyDialog(root.selectedActivityModel, dependencyData)
                }
                onDeleteDependencyRequested: function(dependencyData) {
                    dialogHost.openDeleteDependencyDialog(dependencyData)
                }
                onSaveCalendarRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.saveCalendar(payload)
                    }
                }
                onAddHolidayRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.addHoliday(payload)
                    }
                }
                onDeleteHolidayRequested: function(holidayId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.deleteHoliday(holidayId)
                    }
                }
                onCalculateRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.calculateWorkingDays(payload)
                    }
                }
                onBaselineASelected: function(baselineId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectBaselineA(baselineId)
                    }
                }
                onBaselineBSelected: function(baselineId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectBaselineB(baselineId)
                    }
                }
                onIncludeUnchangedUpdated: function(includeUnchanged) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setIncludeUnchanged(includeUnchanged)
                    }
                }
                onCreateBaselineRequested: function(payload) {
                    dialogHost.openCreateBaselineDialog()
                }
                onDeleteBaselineRequested: function(baselineId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.deleteBaseline(baselineId)
                    }
                }
            }
        }
    }
}
