pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementTasksWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.tasksWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.tasks",
            "title": "Tasks",
            "summary": "Task planning, progress, dependencies, assignments, and execution state.",
            "migrationStatus": "QML task execution workspace active",
            "legacyRuntimeStatus": "QML runtime is active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var tasksModel: root.workspaceController
        ? root.workspaceController.tasks
        : ({
            "title": "Task Catalog",
            "subtitle": "Edit delivery tasks, progress, and execution priorities.",
            "emptyState": "Project-management tasks desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedTaskModel: root.workspaceController
        ? root.workspaceController.selectedTask
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a task from the catalog to review details or update progress.",
            "fields": [],
            "state": {}
        })
    readonly property var assignmentsModel: root.workspaceController
        ? root.workspaceController.assignments
        : ({
            "title": "Assignments",
            "subtitle": "Resource allocations and logged effort for this task.",
            "emptyState": "Select a task to review assignments and effort coverage.",
            "items": []
        })
    readonly property var dependenciesModel: root.workspaceController
        ? root.workspaceController.dependencies
        : ({
            "title": "Dependencies",
            "subtitle": "Sequencing links and lag settings for this task.",
            "emptyState": "Select a task to review predecessor and successor links.",
            "items": []
        })
    readonly property var timeAssignmentSummaryModel: root.workspaceController
        ? root.workspaceController.timeAssignmentSummary
        : ({
            "title": "",
            "subtitle": "",
            "emptyState": "Select a task assignment to review detailed time entries, period status, and labor totals.",
            "fields": [],
            "state": {}
        })
    readonly property var timeEntriesModel: root.workspaceController
        ? root.workspaceController.timeEntries
        : ({
            "title": "Time Entries",
            "subtitle": "Detailed labor entries for the selected task assignment.",
            "emptyState": "Select a task assignment to review or capture labor entries.",
            "items": []
        })
    readonly property var selectedTimeEntryModel: root.workspaceController
        ? root.workspaceController.selectedTimeEntry
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select an entry from the period list to review or edit its captured labor note.",
            "fields": [],
            "state": {}
        })
    readonly property var collaborationCommentsModel: root.workspaceController
        ? root.workspaceController.collaborationComments
        : ({
            "title": "Task Collaboration",
            "subtitle": "Comments, mentions, attachments, and linked shared documents for the selected task.",
            "emptyState": "Select a task to review collaboration updates and post comments.",
            "items": []
        })
    readonly property var collaborationPresenceModel: root.workspaceController
        ? root.workspaceController.collaborationPresence
        : ({
            "title": "Active Presence",
            "subtitle": "People currently reviewing or updating the selected task.",
            "emptyState": "Select a task to review active collaboration presence.",
            "items": []
        })

    readonly property var _tableColumns: [
        { "key": "title",          "label": "Task",      "flex": 2,   "sortable": true  },
        { "key": "statusLabel",    "label": "Status",    "flex": 0,   "minWidth": 100, "type": "status" },
        { "key": "projectName",    "label": "Project",   "flex": 1.5, "sortable": true  },
        { "key": "priorityLabel",  "label": "Priority",  "flex": 0,   "minWidth": 80, "type": "status" },
        { "key": "startDateLabel", "label": "Start",     "flex": 0,   "minWidth": 90    },
        { "key": "endDateLabel",   "label": "Finish",    "flex": 0,   "minWidth": 90    },
        { "key": "progressValue",  "label": "Progress",  "flex": 1,   "minWidth": 110, "type": "progress" }
    ]

    readonly property var _bulkChangeProperties: {
        const properties = []
        const statusOptions = root.workspaceController
            ? (root.workspaceController.bulkStatusOptions || [])
            : []
        if (statusOptions.length > 0) {
            properties.push({
                "id": "status",
                "label": "Status",
                "values": statusOptions
            })
        }
        return properties
    }

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    readonly property var _detailActions: {
        const idx = detailPage ? detailPage.activeSectionIndex : 0
        if (idx === 0) {
            return [
                { "id": "edit",     "label": "Edit",     "icon": "edit",    "enabled": true, "danger": false },
                { "id": "progress", "label": "Progress", "icon": "approve", "enabled": true, "danger": false },
                { "id": "delete",   "label": "Delete",   "icon": "delete",  "enabled": true, "danger": true  }
            ]
        }
        return []
    }

    function _optionIndexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) {
                return i
            }
        }
        return 0
    }
    function _loadLazyDetailSection(sectionIndex) {
        if (root.workspaceController === null) {
            return
        }

        if (sectionIndex === 3) {
            root.workspaceController.loadSelectedTaskTime()
        } else if (sectionIndex === 4) {
            root.workspaceController.loadSelectedTaskCollaboration()
        }
    }

    TasksDialogHost {
        id: dialogHost

        selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
        selectedTaskData: root.selectedTaskModel
        statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
        assignmentOptions: root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []
        dependencyTaskOptions: root.workspaceController ? (root.workspaceController.dependencyTaskOptions || []) : []
        dependencyTypeOptions: root.workspaceController ? (root.workspaceController.dependencyTypeOptions || []) : []
        collaborationMentionOptions: root.workspaceController ? (root.workspaceController.collaborationMentionOptions || []) : []
        collaborationDocumentOptions: root.workspaceController ? (root.workspaceController.collaborationDocumentOptions || []) : []
        selectedTaskIds: root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createTask(payload)
            }
        }
        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateTask(payload)
            }
        }
        onProgressRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateProgress(payload)
            }
        }
        onDeleteRequested: function(taskId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteTask(taskId)
            }
        }
        onCreateAssignmentRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createAssignment(payload)
            }
        }
        onUpdateAssignmentAllocationRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateAssignmentAllocation(payload)
            }
        }
        onSetAssignmentHoursRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.setAssignmentHours(payload)
            }
        }
        onDeleteAssignmentRequested: function(assignmentId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteAssignment(assignmentId)
            }
        }
        onCreateDependencyRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createDependency(payload)
            }
        }
        onDeleteDependencyRequested: function(dependencyId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteDependency(dependencyId)
            }
        }
        onPostTaskCommentRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.postTaskComment(payload)
            }
        }
        onBulkDeleteRequested: function(taskIds) {
            if (root.workspaceController !== null) {
                root.workspaceController.bulkDeleteTasks(taskIds)
            }
        }
        onTaskPresenceStarted: function(taskId, activity) {
            if (root.workspaceController !== null) {
                root.workspaceController.beginTaskPresence(taskId, activity)
            }
        }
        onTaskPresenceEnded: function(taskId) {
            if (root.workspaceController !== null) {
                root.workspaceController.endTaskPresence(taskId)
            }
        }
    }

    // ── Stacked layout: list page / detail page ───────────────────
    Item {
        anchors.fill: parent

        // ── List page (hidden when detail is open) ────────────────
        Item {
            id: _listPage
            anchors.fill: parent
            visible: !detailPage.open

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root.overviewModel.metrics || []
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                        && !(root.workspaceController ? root.workspaceController.isBusy : false)
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "info"
                    message: "Loading tasks..."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.workspaceController
                        ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    tone: "info"
                    message: "Saving task changes..."
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

                AppWidgets.TableToolbar {
                    id: tableToolbar
                    Layout.fillWidth: true
                    searchText: root.workspaceController ? root.workspaceController.searchText : ""
                    searchPlaceholder: "Search tasks..."
                    showCreate: true
                    createLabel: "New Task"
                    showFilter: true
                    showCustomize: true
                    showViews: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setSearchText(text)
                        }
                    }
                    onFilterClicked: filterPopup.open()
                    onCustomizeClicked: tasksTable.openColumnCustomizer()
                    onViewsClicked: savedViewsPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.refresh()
                        }
                    }
                    onExportRequested: {
                        if (root.workspaceController !== null) {
                            root.workspaceController.exportTasks()
                        }
                    }
                    onCreateRequested: dialogHost.openCreateDialog()
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: tasksTable
                        anchors.top:    parent.top
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _paginationBar.top
                        multiSelect: true
                        columns: root._tableColumns
                        rows: root.tasksModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.tasksModel.emptyState || "No tasks available."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedTaskId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) {
                                root.workspaceController.selectTask(rowId)
                            }
                        }
                        onRowActivated: function(rowId) {
                            detailPage.scrollToSection(0)
                            detailPage.open = true

                            if (root.workspaceController !== null) {
                                root.workspaceController.activateTask(rowId)
                            }
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null) {
                                root.workspaceController.setTaskBulkSelection(rowId, selected)
                            }
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) {
                                return
                            }
                            if (allSelected) {
                                root.workspaceController.selectVisibleTasks()
                            } else {
                                root.workspaceController.clearTaskBulkSelection()
                            }
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: parent.bottom
                        currentPage:  root.workspaceController ? root.workspaceController.taskPage     : 1
                        pageSize:     root.workspaceController ? root.workspaceController.taskPageSize  : 25
                        totalItems:   root.workspaceController ? root.workspaceController.taskTotalCount : 0
                        busy:         root.workspaceController ? root.workspaceController.isBusy        : false
                        onPageRequested: function(page) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setTaskPage(page)
                        }
                        onPageSizeRequested: function(pageSize) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setTaskPageSize(pageSize)
                        }
                    }

                    Popup {
                        id: filterPopup
                        parent: tableToolbar
                        width: 304
                        padding: Theme.AppTheme.marginMd
                        x: tableToolbar.width - width
                        y: tableToolbar.height + Theme.AppTheme.spacingXs
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
                                text: "Project"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.projectOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedProjectId : ""
                                )
                                onActivated: function(index) {
                                    const options = root.workspaceController
                                        ? (root.workspaceController.projectOptions || [])
                                        : []
                                    if (root.workspaceController !== null && options[index]) {
                                        root.workspaceController.selectProject(String(options[index].value || ""))
                                    }
                                }
                            }

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
                                currentIndex: root._optionIndexForValue(
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

                            Label {
                                text: "Priority"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.priorityOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.priorityOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedPriorityFilter : "all"
                                )
                                onActivated: function(index) {
                                    const options = root.workspaceController
                                        ? (root.workspaceController.priorityOptions || [])
                                        : []
                                    if (root.workspaceController !== null && options[index]) {
                                        root.workspaceController.setPriorityFilter(String(options[index].value || "all"))
                                    }
                                }
                            }

                            Label {
                                text: "Schedule"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.scheduleOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.scheduleOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedScheduleFilter : "all"
                                )
                                onActivated: function(index) {
                                    const options = root.workspaceController
                                        ? (root.workspaceController.scheduleOptions || [])
                                        : []
                                    if (root.workspaceController !== null && options[index]) {
                                        root.workspaceController.setScheduleFilter(String(options[index].value || "all"))
                                    }
                                }
                            }

                            Label {
                                text: "Saved View"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.taskViewOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.taskViewOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedTaskViewName : ""
                                )
                                onActivated: function(index) {
                                    const options = root.workspaceController
                                        ? (root.workspaceController.taskViewOptions || [])
                                        : []
                                    if (root.workspaceController !== null && options[index]) {
                                        root.workspaceController.selectTaskView(String(options[index].value || ""))
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

                                AppControls.PrimaryButton {
                                    Layout.fillWidth: true
                                    text: "Apply View"
                                    iconName: "register"
                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                    onClicked: {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.applySelectedTaskView()
                                        }
                                        filterPopup.close()
                                    }
                                }
                            }
                        }
                    }

                    Popup {
                        id: savedViewsPopup
                        parent: tableToolbar
                        width: 260
                        padding: Theme.AppTheme.marginMd
                        x: tableToolbar.width - width
                        y: tableToolbar.height + Theme.AppTheme.spacingXs
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
                                text: "Saved Views"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.taskViewOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.taskViewOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedTaskViewName : ""
                                )
                                onActivated: function(index) {
                                    const options = root.workspaceController
                                        ? (root.workspaceController.taskViewOptions || [])
                                        : []
                                    if (root.workspaceController !== null && options[index]) {
                                        root.workspaceController.selectTaskView(String(options[index].value || ""))
                                    }
                                }
                            }

                            AppControls.PrimaryButton {
                                Layout.fillWidth: true
                                text: "Apply View"
                                iconName: "register"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                onClicked: {
                                    if (root.workspaceController !== null) {
                                        root.workspaceController.applySelectedTaskView()
                                    }
                                    savedViewsPopup.close()
                                }
                            }
                        }
                    }

                    AppWidgets.BulkActionBar {
                        id: bulkActionBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        selectedCount: root.workspaceController ? root.workspaceController.selectedTaskCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "delete", "label": "Delete", "icon": "delete", "danger": true, "enabled": true },
                            { "id": "change_property", "label": "Change Property", "icon": "edit", "danger": false, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) {
                                root.workspaceController.clearTaskBulkSelection()
                            }
                        }
                        onActionTriggered: function(actionId) {
                            if (actionId === "delete") {
                                dialogHost.openBulkDeleteDialog(
                                    root.workspaceController ? (root.workspaceController.selectedTaskIds || []) : []
                                )
                            } else if (actionId === "change_property") {
                                bulkChangePropertyPopup.open()
                            }
                        }
                    }

                    AppWidgets.BulkChangePropertyPopup {
                        id: bulkChangePropertyPopup
                        parent: bulkActionBar
                        x: Math.round((bulkActionBar.width - width) / 2)
                        y: -height - Theme.AppTheme.spacingXs
                        selectedCount: root.workspaceController ? root.workspaceController.selectedTaskCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        properties: root._bulkChangeProperties

                        onApplyRequested: function(payload) {
                            if (root.workspaceController === null) {
                                return
                            }
                            if (payload.propertyId === "status") {
                                root.workspaceController.applyBulkStatus({ "status": payload.value })
                            }
                        }
                    }
                }
            }
        }

        // ── Detail page (covers full area, z:20) ──────────────────
        AppWidgets.SectionDetailPage {
            id: detailPage
            anchors.fill: parent
            open: false
            showHeader: false
            showEdit: false
            showDelete: false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
            sections: [
                    "Details",
                    { "label": "Assignments",  "count": (root.assignmentsModel.items   || []).length },
                    { "label": "Dependencies", "count": (root.dependenciesModel.items  || []).length },
                    { "label": "Time",         "count": (root.timeEntriesModel.items   || []).length },
                    { "label": "Activity",     "count": (root.collaborationCommentsModel.items || []).length }
                ]
            z: 20

            onSectionChanged: function(index) {
                root._loadLazyDetailSection(index)
            }

            AppWidgets.ContextualActionToolbar {
                width: parent ? parent.width : 0
                showBack: true
                title: root.selectedTaskModel.title || "Task Details"
                subtitle: root.selectedTaskModel.statusLabel || root.selectedTaskModel.subtitle || ""
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: root._detailActions

                onBackRequested: {
                    detailPage.open = false
                    detailPage.scrollToSection(0)
                }
                onActionTriggered: function(actionId) {
                    if (actionId === "edit") {
                        dialogHost.openEditDialog(root.selectedTaskModel)
                    } else if (actionId === "progress") {
                        dialogHost.openProgressDialog(root.selectedTaskModel)
                    } else if (actionId === "delete") {
                        dialogHost.openDeleteDialog(root.selectedTaskModel)
                    }
                }
            }

            TasksDetailPanel {
                width: parent ? parent.width : 0
                detailPage: detailPage
                taskDetail: root.selectedTaskModel
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                assignmentsModel: root.assignmentsModel
                selectedAssignmentId: root.workspaceController ? root.workspaceController.selectedAssignmentId : ""
                assignmentOptions: root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []

                dependenciesModel: root.dependenciesModel
                dependencyTaskOptions: root.workspaceController ? (root.workspaceController.dependencyTaskOptions || []) : []

                timeAssignmentSummaryModel: root.timeAssignmentSummaryModel
                timeEntriesModel: root.timeEntriesModel
                selectedTimeEntryModel: root.selectedTimeEntryModel
                selectedEntryId: root.workspaceController ? root.workspaceController.selectedTimeEntryId : ""
                periodOptions: root.workspaceController ? (root.workspaceController.timePeriodOptions || []) : []
                selectedPeriodStart: root.workspaceController ? root.workspaceController.selectedTimePeriodStart : ""

                collaborationCommentsModel: root.collaborationCommentsModel
                collaborationPresenceModel: root.collaborationPresenceModel
                selectedTaskId: root.workspaceController ? root.workspaceController.selectedTaskId : ""

                onCreateAssignmentRequested: dialogHost.openCreateAssignmentDialog(root.selectedTaskModel)
                onAssignmentSelected: function(assignmentId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectAssignment(assignmentId)
                    }
                }
                onEditAllocationRequested: function(assignmentData) {
                    dialogHost.openEditAssignmentAllocationDialog(assignmentData, root.selectedTaskModel)
                }
                onSetHoursRequested: function(assignmentData) {
                    dialogHost.openAssignmentHoursDialog(assignmentData)
                }
                onDeleteAssignmentRequested: function(assignmentData) {
                    dialogHost.openDeleteAssignmentDialog(assignmentData)
                }

                onCreateDependencyRequested: dialogHost.openCreateDependencyDialog(root.selectedTaskModel)
                onDeleteDependencyRequested: function(dependencyData) {
                    dialogHost.openDeleteDependencyDialog(dependencyData)
                }

                onPeriodChanged: function(periodStart) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectTimePeriod(periodStart)
                    }
                }
                onEntrySelected: function(entryId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectTimeEntry(entryId)
                    }
                }
                onTimeAddRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.addTaskTimeEntry(payload)
                    }
                }
                onTimeUpdateRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.updateTaskTimeEntry(payload)
                    }
                }
                onTimeDeleteRequested: function(entryId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.deleteTaskTimeEntry(entryId)
                    }
                }
                onTimeSubmitRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.submitTaskPeriod(payload)
                    }
                }
                onTimeLockRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.lockTaskPeriod(payload)
                    }
                }
                onTimeUnlockRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.unlockTaskPeriod(payload)
                    }
                }

                onComposeRequested: dialogHost.openTaskCollaborationDialog(root.selectedTaskModel)
                onMarkReadRequested: function(taskId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.markTaskCollaborationRead(taskId)
                    }
                }
                onCollaborationRefreshRequested: {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }
            }
        }
    }
}
