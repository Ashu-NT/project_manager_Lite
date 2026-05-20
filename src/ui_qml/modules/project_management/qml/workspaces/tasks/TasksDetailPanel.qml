pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    // ── Core detail ──────────────────────────────────────────────────────
    property var taskDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "", "fields": [], "state": {}
    })
    property bool isBusy: false
    property var detailPage: null

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

    implicitHeight: _mainCol.implicitHeight

    Column {
        id: _mainCol
        width: parent.width
        spacing: 0

        // ── Section 0: Details ───────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 0; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Details" }

        Item {
            width: parent.width
            implicitHeight: detailsContent.implicitHeight + Theme.AppTheme.spacingMd * 2

            ColumnLayout {
                id: detailsContent
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                anchors.bottomMargin: Theme.AppTheme.spacingMd
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
                    id: progressStrip
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
                    visible: String(root.taskDetail.id || "").length > 0 && progressStrip._progressValue > 0

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
                            value: progressStrip._progressValue
                            implicitHeight: 6
                        }

                        Label {
                            text: progressStrip._progressLabel
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

                    delegate: Item {
                        id: fieldCard
                        required property var modelData

                        Layout.fillWidth: true
                        implicitHeight: fieldLayout.implicitHeight + Theme.AppTheme.spacingMd + 1

                        ColumnLayout {
                            id: fieldLayout
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.leftMargin: Theme.AppTheme.spacingSm
                            anchors.rightMargin: Theme.AppTheme.spacingSm
                            anchors.topMargin: Theme.AppTheme.spacingSm
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

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: Theme.AppTheme.divider
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

                    AppControls.SecondaryButton {
                        text: "Progress"
                        enabled: !root.isBusy
                        onClicked: root.progressRequested()
                    }

                    AppControls.SecondaryButton {
                        text: "Delete"
                        danger: true
                        enabled: !root.isBusy
                        onClicked: root.deleteRequested()
                    }

                    Item { Layout.fillWidth: true }
                }
            }
        }

        // ── Section 1: Assignments ───────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 1; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Assignments" }

        Item {
            width: parent.width
            implicitHeight: assignmentsInner.implicitHeight + Theme.AppTheme.spacingMd * 2

            TasksAssignmentsSection {
                id: assignmentsInner
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd

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

        // ── Section 2: Dependencies ──────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 2; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Dependencies" }

        Item {
            width: parent.width
            implicitHeight: dependenciesInner.implicitHeight + Theme.AppTheme.spacingMd * 2

            TasksDependenciesSection {
                id: dependenciesInner
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd

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

        // ── Section 3: Time ──────────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 3; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Time" }

        Item {
            width: parent.width
            implicitHeight: timeInner.implicitHeight + Theme.AppTheme.spacingMd * 2

            TasksTimeEntriesSection {
                id: timeInner
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd

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

        // ── Section 4: Activity ──────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 4; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Activity" }

        Item {
            width: parent.width
            implicitHeight: collaborationInner.implicitHeight + Theme.AppTheme.spacingMd * 2

            TasksCollaborationSection {
                id: collaborationInner
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd

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
