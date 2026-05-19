pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    // ── Core detail ──────────────────────────────────────────────────────
    property var taskDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "", "fields": [], "state": {}
    })
    property bool isBusy: false

    // ── Sub-panel data ────────────────────────────────────────────────────
    property var assignmentsModel: ({
        "title": "Assignments", "subtitle": "", "emptyState": "Select a task.", "items": []
    })
    property string selectedAssignmentId: ""
    property var assignmentOptions: []

    property var dependenciesModel: ({
        "title": "Dependencies", "subtitle": "", "emptyState": "Select a task.", "items": []
    })
    property var dependencyTaskOptions: []

    property var timeAssignmentSummaryModel: ({
        "title": "", "subtitle": "", "emptyState": "Select a task assignment.", "fields": [], "state": {}
    })
    property var timeEntriesModel: ({
        "title": "Time Entries", "subtitle": "", "emptyState": "Select a task assignment.", "items": []
    })
    property var selectedTimeEntryModel: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "", "fields": [], "state": {}
    })
    property string selectedEntryId: ""
    property var periodOptions: []
    property string selectedPeriodStart: ""

    property var collaborationCommentsModel: ({
        "title": "Collaboration", "subtitle": "", "emptyState": "Select a task.", "items": []
    })
    property var collaborationPresenceModel: ({
        "title": "Active Presence", "subtitle": "", "emptyState": "Select a task.", "items": []
    })
    property string selectedTaskId: ""

    // ── Signals ───────────────────────────────────────────────────────────
    signal editRequested()
    signal progressRequested()
    signal deleteRequested()

    signal createAssignmentRequested()
    signal assignmentSelected(string assignmentId)
    signal editAllocationRequested(var assignmentData)
    signal setHoursRequested(var assignmentData)
    signal deleteAssignmentRequested(var assignmentData)

    signal createDependencyRequested()
    signal deleteDependencyRequested(var dependencyData)

    signal periodChanged(string periodStart)
    signal entrySelected(string entryId)
    signal timeAddRequested(var payload)
    signal timeUpdateRequested(var payload)
    signal timeDeleteRequested(string entryId)
    signal timeSubmitRequested(var payload)
    signal timeLockRequested(var payload)
    signal timeUnlockRequested(var payload)

    signal composeRequested()
    signal markReadRequested(string taskId)
    signal collaborationRefreshRequested()

    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    border.width: 1
    radius: Theme.AppTheme.radiusMd
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Tab bar ──────────────────────────────────────────────────────
        AppWidgets.DetailTabBar {
            id: tabBar
            Layout.fillWidth: true
            tabs: ["Details", "Assignments", "Dependencies", "Time", "Activity"]
            currentIndex: 0
            onTabSelected: function(index) { tabBar.currentIndex = index }
        }

        // ── Tab content ──────────────────────────────────────────────────
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            // ── Tab 0: Details ───────────────────────────────────────────
            Flickable {
                clip: true
                contentWidth: width
                contentHeight: detailsContent.implicitHeight + Theme.AppTheme.spacingLg
                ScrollBar.vertical: ScrollBar {}

                ColumnLayout {
                    id: detailsContent
                    width: parent.width
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: Theme.AppTheme.spacingMd
                    spacing: Theme.AppTheme.spacingMd

                    // Header: title + status chip
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingXs

                            Label {
                                Layout.fillWidth: true
                                text: root.taskDetail.title || "Task Detail"
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }

                            Label {
                                Layout.fillWidth: true
                                text: root.taskDetail.subtitle || "Select a task to inspect details."
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WordWrap
                            }
                        }

                        AppWidgets.StatusChip {
                            visible: String(root.taskDetail.statusLabel || "").length > 0
                            status: root.taskDetail.statusLabel || ""
                        }
                    }

                    // Empty state
                    Label {
                        Layout.fillWidth: true
                        visible: String(root.taskDetail.emptyState || "").length > 0
                            && String(root.taskDetail.id || "").length === 0
                        text: root.taskDetail.emptyState || ""
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }

                    // Progress bar strip
                    Item {
                        Layout.fillWidth: true
                        height: 28
                        visible: String(root.taskDetail.id || "").length > 0 && _progressValue > 0

                        readonly property real _progressValue: {
                            const state = root.taskDetail.state || {}
                            return parseFloat(state.percentComplete || "0") / 100.0
                        }
                        readonly property string _progressLabel: {
                            const state = root.taskDetail.state || {}
                            return state.percentCompleteLabel || ""
                        }

                        RowLayout {
                            anchors.fill: parent
                            spacing: Theme.AppTheme.spacingSm

                            Label {
                                text: "Progress"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            AppWidgets.ProgressBar {
                                Layout.fillWidth: true
                                value: parent.parent._progressValue
                                implicitHeight: 6
                            }

                            Label {
                                text: parent.parent._progressLabel
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                        }
                    }

                    // Description
                    Label {
                        Layout.fillWidth: true
                        visible: String(root.taskDetail.id || "").length > 0
                            && String(root.taskDetail.description || "").length > 0
                        text: root.taskDetail.description || ""
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        wrapMode: Text.WordWrap
                    }

                    // Field cards
                    Repeater {
                        model: root.taskDetail.fields || []

                        delegate: Rectangle {
                            id: fieldCard
                            required property var modelData

                            Layout.fillWidth: true
                            radius: Theme.AppTheme.radiusMd
                            color: Theme.AppTheme.surfaceAlt
                            implicitHeight: fieldLayout.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: fieldLayout
                                anchors.fill: parent
                                anchors.margins: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingXs

                                Label {
                                    Layout.fillWidth: true
                                    text: String(fieldCard.modelData.label || "")
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: String(fieldCard.modelData.value || "")
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    wrapMode: Text.WordWrap
                                }

                                Label {
                                    Layout.fillWidth: true
                                    visible: String(fieldCard.modelData.supportingText || "").length > 0
                                    text: String(fieldCard.modelData.supportingText || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }

                    // Action buttons
                    RowLayout {
                        Layout.fillWidth: true
                        visible: String(root.taskDetail.id || "").length > 0
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.PrimaryButton {
                            text: "Edit"
                            enabled: !root.isBusy
                            onClicked: root.editRequested()
                        }

                        AppControls.PrimaryButton {
                            text: "Progress"
                            enabled: !root.isBusy
                            onClicked: root.progressRequested()
                        }

                        AppControls.PrimaryButton {
                            text: "Delete"
                            danger: true
                            enabled: !root.isBusy
                            onClicked: root.deleteRequested()
                        }

                        Item { Layout.fillWidth: true }
                    }
                }
            }

            // ── Tab 1: Assignments ───────────────────────────────────────
            Flickable {
                clip: true
                contentWidth: width
                contentHeight: assignmentsInner.implicitHeight + Theme.AppTheme.spacingLg
                ScrollBar.vertical: ScrollBar {}

                TasksAssignmentsSection {
                    id: assignmentsInner
                    width: parent.width
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right

                    assignmentsModel: root.assignmentsModel
                    selectedAssignmentId: root.selectedAssignmentId
                    isBusy: root.isBusy
                    canCreate: String(root.taskDetail.id || "").length > 0
                        && root.assignmentOptions.length > 0

                    onCreateRequested: root.createAssignmentRequested()
                    onAssignmentSelected: function(assignmentId) {
                        root.assignmentSelected(assignmentId)
                    }
                    onEditAllocationRequested: function(assignmentData) {
                        root.editAllocationRequested(assignmentData)
                    }
                    onSetHoursRequested: function(assignmentData) {
                        root.setHoursRequested(assignmentData)
                    }
                    onDeleteRequested: function(assignmentData) {
                        root.deleteAssignmentRequested(assignmentData)
                    }
                }
            }

            // ── Tab 2: Dependencies ──────────────────────────────────────
            Flickable {
                clip: true
                contentWidth: width
                contentHeight: dependenciesInner.implicitHeight + Theme.AppTheme.spacingLg
                ScrollBar.vertical: ScrollBar {}

                TasksDependenciesSection {
                    id: dependenciesInner
                    width: parent.width
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right

                    dependenciesModel: root.dependenciesModel
                    isBusy: root.isBusy
                    canCreate: String(root.taskDetail.id || "").length > 0
                        && root.dependencyTaskOptions.length > 0

                    onCreateRequested: root.createDependencyRequested()
                    onDeleteRequested: function(dependencyData) {
                        root.deleteDependencyRequested(dependencyData)
                    }
                }
            }

            // ── Tab 3: Time ──────────────────────────────────────────────
            Flickable {
                clip: true
                contentWidth: width
                contentHeight: timeInner.implicitHeight + Theme.AppTheme.spacingLg
                ScrollBar.vertical: ScrollBar {}

                TasksTimeEntriesSection {
                    id: timeInner
                    width: parent.width
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right

                    assignmentSummary: root.timeAssignmentSummaryModel
                    periodOptions: root.periodOptions
                    selectedPeriodStart: root.selectedPeriodStart
                    entriesModel: root.timeEntriesModel
                    selectedEntryDetail: root.selectedTimeEntryModel
                    selectedEntryId: root.selectedEntryId
                    isBusy: root.isBusy

                    onPeriodChanged: function(periodStart) { root.periodChanged(periodStart) }
                    onEntrySelected: function(entryId) { root.entrySelected(entryId) }
                    onAddRequested: function(payload) { root.timeAddRequested(payload) }
                    onUpdateRequested: function(payload) { root.timeUpdateRequested(payload) }
                    onDeleteRequested: function(entryId) { root.timeDeleteRequested(entryId) }
                    onSubmitRequested: function(payload) { root.timeSubmitRequested(payload) }
                    onLockRequested: function(payload) { root.timeLockRequested(payload) }
                    onUnlockRequested: function(payload) { root.timeUnlockRequested(payload) }
                }
            }

            // ── Tab 4: Activity ──────────────────────────────────────────
            Flickable {
                clip: true
                contentWidth: width
                contentHeight: collaborationInner.implicitHeight + Theme.AppTheme.spacingLg
                ScrollBar.vertical: ScrollBar {}

                TasksCollaborationSection {
                    id: collaborationInner
                    width: parent.width
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right

                    commentsModel: root.collaborationCommentsModel
                    presenceModel: root.collaborationPresenceModel
                    selectedTaskId: root.selectedTaskId
                    isBusy: root.isBusy
                    canCompose: String(root.taskDetail.id || "").length > 0

                    onComposeRequested: root.composeRequested()
                    onMarkReadRequested: function(taskId) { root.markReadRequested(taskId) }
                    onRefreshRequested: root.collaborationRefreshRequested()
                }
            }
        }
    }
}
