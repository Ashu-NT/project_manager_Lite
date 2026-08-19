pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Mock 1.0 as AppMock
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as PMWidgets
import workspaces.tasks.sections 1.0

Item {
    id: root

    property var taskDetail: AppMock.MockFactory.detail()
    property bool isBusy: false
    property var detailPage: null

    property var assignmentsModel: AppMock.MockFactory.catalog("Assignments", "", "Select a task.")
    property var assignmentsTableModel: null
    property string selectedAssignmentId: ""
    property var assignmentOptions: []
    property var projectResourceUsage: null

    property var dependenciesModel: AppMock.MockFactory.catalog("Dependencies", "", "Select a task.")
    property var dependenciesTableModel: null
    property var dependencyTypeOptions: []
    property var selectedDependencyItem: null
    property var dependencyTaskOptions: []
    property var dependencyImpactPreview: ({})

    property var taskTimeSummary: ({ "hasSummary": false })
    property var taskTimeEntriesPage: ({ "items": [], "total": 0, "page": 1, "pageSize": 25 })
    property var timeEntriesTableModel: null
    property var selectedTimeEntryModel: AppMock.MockFactory.detail()
    property string selectedEntryId: ""
    property var timeAssignmentOptions: []
    property string timeResourceFilter: ""

    property var collaborationCommentsModel: AppMock.MockFactory.catalog("Collaboration", "", "Select a task.")
    property var collaborationPresenceModel: AppMock.MockFactory.catalog("Active Presence", "", "Select a task.")
    property string selectedTaskId: ""
    property bool canOpenReservations: false
    property bool canOpenProcurement: false

    property var skillRequirementsModel: AppMock.MockFactory.catalog("Skill Requirements", "", "Select a task.")
    property var taskActivityModel: ({
        "title": "Activity", "subtitle": "", "emptyState": "No activity has been recorded for this task yet.", "items": []
    })
    property var sectionErrors: ({})
    property var scheduleImpactModel: ({
        "available": false,
        "taskId": "",
        "summary": "Select a task to view schedule impact analysis.",
        "rows": [],
        "affectedCount": 0,
        "maxProjectFinishShiftDays": 0,
        "requiresApproval": false,
        "approvalLabel": "",
        "newlyCriticalCount": 0,
        "noLongerCriticalCount": 0
    })

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog

    signal editRequested()
    signal progressRequested()
    signal deleteRequested()
    signal retrySectionRequested(string sectionName)
    signal manageProjectResourcesRequested()

    signal createAssignmentRequested()
    signal assignmentSelected(string assignmentId)
    signal assignmentPreviewRequested(string projectResourceId, string taskId)
    signal editAllocationRequested(var assignmentData)
    signal editPlannedHoursRequested(var assignmentData)
    signal deleteAssignmentRequested(var assignmentData)
    signal acceptAssignmentRequested(var assignmentData)
    signal declineAssignmentRequested(var assignmentData)

    signal createDependencyRequested()
    signal editDependencyRequested(var payload)
    signal deleteDependencyRequested(var dependencyData)
    signal dependencySelectionChanged(var dependencyData)
    signal openTaskRequested(string taskId)
    signal dependencyPreviewRequested(string dependencyId)

    signal timeResourceFilterRequested(string resourceId)
    signal timePageRequested(int page)
    signal entrySelected(string entryId)
    signal timeAddRequested(var payload)
    signal timeUpdateRequested(var payload)
    signal timeDeleteRequested(string entryId)
    signal goToAssignmentRequested(string assignmentId)
    signal openTimesheetsRequested()

    signal composeRequested()
    signal commentReplyRequested(var commentData)
    signal commentEditRequested(var commentData)
    signal commentDeleteRequested(var commentData)
    signal commentReactionRequested(var payload)
    signal commentReactionRemovalRequested(var payload)
    signal markReadRequested(string taskId)
    signal collaborationRefreshRequested()
    signal openReservationsRequested()
    signal openProcurementRequested()

    readonly property real _progressValue: {
        const s = root.taskDetail.state || {}
        return parseFloat(s.percentComplete || "0") / 100.0
    }
    readonly property string _progressLabel: {
        const s = root.taskDetail.state || {}
        return String(s.percentCompleteLabel || "")
    }
    readonly property bool _hasTask: String(root.taskDetail.id || "").length > 0
    readonly property bool _isSummary: Boolean((root.taskDetail.state || {}).isSummary)
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property var _sections: root.detailPage ? (root.detailPage.sections || []) : []

    function _secIdx(name) {
        const secs = root._sections
        for (let i = 0; i < secs.length; i++) {
            const s = secs[i]
            const sLabel = (typeof s === "string") ? s : (s.label || "")
            if (sLabel === name) return i
        }
        return -1
    }

    function _clearDependencySelection() {
        if (root.selectedDependencyItem === null) return
        root.selectedDependencyItem = null
        root.dependencySelectionChanged(null)
    }

    function openSelectedDependencyEditor() {
        if (root.selectedDependencyItem) {
            root.editDependencyRequested(root.selectedDependencyItem)
        }
    }

    on_IdxChanged: {
        const entry = root._sections[root._idx] || ""
        const name = (typeof entry === "string") ? entry : (entry.label || "")
        if (name !== "Dependencies") {
            root._clearDependencySelection()
        }
    }

    onTaskDetailChanged: root._clearDependencySelection()

    implicitHeight: (_summaryStrip.visible ? _summaryStrip.height : 0)
        + _activeSectionH
        + Theme.AppTheme.spacingLg
    height: implicitHeight

    readonly property int _activeSectionH: {
        const secs = root._sections
        const entry = (secs.length > root._idx) ? secs[root._idx] : null
        const name = entry ? ((typeof entry === "string") ? entry : (entry.label || "")) : ""
        if (name === "Details")         return _sec0.implicitHeight
        if (name === "Assignments")     return _sec1.implicitHeight
        if (name === "Dependencies")    return _sec2.implicitHeight
        if (name === "Time")            return _sec3.implicitHeight
        if (name === "Discussion")      return _sec4.implicitHeight
        if (name === "Material Demand") return _sec5.implicitHeight
        if (name === "Skills")          return _sec6.implicitHeight
        if (name === "Schedule Impact") return _sec7.implicitHeight
        if (name === "Activity")        return _sec8.implicitHeight
        return 0
    }

    Rectangle {
        id: _summaryStrip
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 40
        color: Theme.AppTheme.surfaceAlt
        visible: false

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Theme.AppTheme.divider
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.AppTheme.marginMd
            anchors.rightMargin: Theme.AppTheme.marginMd
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.StatusChip {
                visible: String(root.taskDetail.statusLabel || "").length > 0
                status: root.taskDetail.statusLabel || ""
            }

            RowLayout {
                visible: root._progressValue > 0
                spacing: Theme.AppTheme.spacingXs

                AppWidgets.ProgressBar {
                    implicitWidth: 90
                    value: root._progressValue
                }

                AppControls.Label {
                    text: root._progressLabel
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }
            }

            Rectangle {
                Layout.preferredWidth: 1; Layout.preferredHeight: 14
                color: Theme.AppTheme.divider
                visible: String(root.taskDetail.subtitle || "").length > 0
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: root.taskDetail.subtitle || ""
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                elide: Text.ElideRight
                visible: text.length > 0
            }
        }
    }

    Item {
        id: _sectionArea
        anchors.top: _summaryStrip.visible ? _summaryStrip.bottom : parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: root._activeSectionH

        AppWidgets.LazySectionLoader {
            id: _sec0
            active: root._idx === root._secIdx("Details")
            loadingMessage: "Loading task details..."
            sourceComponent: Component {
                TasksDetailsSection {
                    width: parent ? parent.width : 0
                    taskDetail: root.taskDetail
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec1
            active: root._idx === root._secIdx("Assignments")
            loadingMessage: "Loading assignments..."
            sourceComponent: Component {
                TasksAssignmentsSection {
                    width: parent ? parent.width : 0
                    assignmentsModel: root.assignmentsModel
                    assignmentsTableModel: root.assignmentsTableModel
                    selectedAssignmentId: root.selectedAssignmentId
                    projectResourceUsage: root.projectResourceUsage
                    taskDetail: root.taskDetail
                    isBusy: root.isBusy
                    canCreate: root._hasTask && !root._isSummary && root.assignmentOptions.length > 0
                    errorText: String(root.sectionErrors["assignments"] || "")

                    onCreateRequested: root.createAssignmentRequested()
                    onAssignmentSelected: function(id) { root.assignmentSelected(id) }
                    onPreviewRequested: function(projectResourceId, taskId) {
                        root.assignmentPreviewRequested(projectResourceId, taskId)
                    }
                    onRetryRequested: root.retrySectionRequested("Assignments")
                    onEditAllocationRequested: function(d) { root.editAllocationRequested(d) }
                    onEditPlannedHoursRequested: function(d) { root.editPlannedHoursRequested(d) }
                    onDeleteRequested: function(d) { root.deleteAssignmentRequested(d) }
                    onAcceptRequested: function(d) { root.acceptAssignmentRequested(d) }
                    onDeclineRequested: function(d) { root.declineAssignmentRequested(d) }
                    onManageProjectResourcesRequested: root.manageProjectResourcesRequested()
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec2
            active: root._idx === root._secIdx("Dependencies")
            loadingMessage: "Loading dependencies..."
            sourceComponent: Component {
                TasksDependenciesSection {
                    width: parent ? parent.width : 0
                    dependenciesModel: root.dependenciesModel
                    isBusy: root.isBusy
                    canCreate: root._hasTask && !root._isSummary && root.dependencyTaskOptions.length > 0
                    errorText: String(root.sectionErrors["dependencies"] || "")
                    dependencyTypeOptions: root.dependencyTypeOptions || []
                    taskDetail: root.taskDetail
                    dependencyImpactPreview: root.dependencyImpactPreview

                    onCreateRequested: root.createDependencyRequested()
                    onSelectionChanged: function(dependencyData) {
                        root.selectedDependencyItem = dependencyData || null
                        root.dependencySelectionChanged(root.selectedDependencyItem)
                    }
                    onEditRequested: function(payload) { root.editDependencyRequested(payload) }
                    onDeleteRequested: function(d) { root.deleteDependencyRequested(d) }
                    onOpenTaskRequested: function(taskId) { root.openTaskRequested(taskId) }
                    onPreviewRequested: function(dependencyId) { root.dependencyPreviewRequested(dependencyId) }
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec3
            active: root._idx === root._secIdx("Time")
            loadingMessage: "Loading time entries..."
            sourceComponent: Component {
                TasksTimeEntriesSection {
                    width: parent ? parent.width : 0
                    taskTimeSummary: root.taskTimeSummary
                    assignmentOptions: root.timeAssignmentOptions
                    taskTimeEntriesPage: root.taskTimeEntriesPage
                    entriesTableModel: root.timeEntriesTableModel
                    timeResourceFilter: root.timeResourceFilter
                    selectedEntryDetail: root.selectedTimeEntryModel
                    selectedEntryId: root.selectedEntryId
                    isBusy: root.isBusy
                    errorText: String(root.sectionErrors["time"] || "")

                    onResourceFilterRequested: function(resourceId) { root.timeResourceFilterRequested(resourceId) }
                    onPageRequested: function(page) { root.timePageRequested(page) }
                    onEntrySelected: function(id) { root.entrySelected(id) }
                    onAddRequested: function(pl) { root.timeAddRequested(pl) }
                    onUpdateRequested: function(pl) { root.timeUpdateRequested(pl) }
                    onDeleteRequested: function(id) { root.timeDeleteRequested(id) }
                    onOpenTimesheetsRequested: root.openTimesheetsRequested()
                    onGoToAssignmentRequested: function(assignmentId) { root.goToAssignmentRequested(assignmentId) }
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec4
            active: root._idx === root._secIdx("Discussion")
            loadingMessage: "Loading discussion..."
            sourceComponent: Component {
                TasksCollaborationSection {
                    width: parent ? parent.width : 0
                    commentsModel: root.collaborationCommentsModel
                    presenceModel: root.collaborationPresenceModel
                    selectedTaskId: root.selectedTaskId
                    isBusy: root.isBusy
                    canCompose: root._hasTask
                    errorText: String(root.sectionErrors["discussion"] || "")

                    onComposeRequested: root.composeRequested()
                    onReplyRequested: function(item) { root.commentReplyRequested(item) }
                    onEditRequested: function(item) { root.commentEditRequested(item) }
                    onDeleteRequested: function(item) { root.commentDeleteRequested(item) }
                    onReactionRequested: function(payload) {
                        root.commentReactionRequested(payload)
                    }
                    onReactionRemovalRequested: function(payload) {
                        root.commentReactionRemovalRequested(payload)
                    }
                    onMarkReadRequested: function(id) { root.markReadRequested(id) }
                    onRefreshRequested: root.collaborationRefreshRequested()
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec5
            active: root._idx === root._secIdx("Material Demand")
            loadingMessage: "Loading..."
            sourceComponent: Component {
                TasksMaterialDemandSection {
                    width: parent ? parent.width : 0
                    taskDetail: root.taskDetail
                    canOpenReservations: root.canOpenReservations
                    canOpenProcurement: root.canOpenProcurement
                    isBusy: root.isBusy
                    onOpenReservationsRequested: root.openReservationsRequested()
                    onOpenProcurementRequested: root.openProcurementRequested()
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec6
            active: root._idx === root._secIdx("Skills")
            loadingMessage: "Loading..."
            sourceComponent: Component {
                TasksSkillsSection {
                    width: parent ? parent.width : 0
                    skillRequirementsModel: root.skillRequirementsModel
                    sectionErrors: root.sectionErrors
                    isBusy: root.isBusy
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec7
            active: root._idx === root._secIdx("Schedule Impact")
            loadingMessage: "Loading..."
            sourceComponent: Component {
                TasksScheduleImpactSection {
                    width: parent ? parent.width : 0
                    scheduleImpactModel: root.scheduleImpactModel
                    sectionErrors: root.sectionErrors
                    isBusy: root.isBusy
                }
            }
        }

        AppWidgets.LazySectionLoader {
            id: _sec8
            active: root._idx === root._secIdx("Activity")
            loadingMessage: "Loading activity..."
            sourceComponent: Component {
                PMWidgets.ActivityLogSection {
                    width: parent ? parent.width : 0
                    label: "Activity"
                    errorKey: "activity"
                    sectionErrors: root.sectionErrors
                    activityModel: root.taskActivityModel
                }
            }
        }
    }
}
