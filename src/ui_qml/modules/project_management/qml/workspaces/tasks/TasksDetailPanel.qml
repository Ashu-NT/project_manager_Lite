pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Mock 1.0 as AppMock
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    // ── Core detail ───────────────────────────────────────────────────
    property var  taskDetail: AppMock.MockFactory.detail()
    property bool isBusy:    false
    property var  detailPage: null

    // ── Sub-panel data ────────────────────────────────────────────────
    property var    assignmentsModel:     AppMock.MockFactory.catalog("Assignments", "", "Select a task.")
    property string selectedAssignmentId: ""
    property var    assignmentOptions:    []

    property var dependenciesModel:    AppMock.MockFactory.catalog("Dependencies", "", "Select a task.")
    property var dependencyTaskOptions: []

    property var    timeAssignmentSummaryModel: AppMock.MockFactory.fieldRecord("", "", "Select a task assignment.")
    property var    timeEntriesModel:           AppMock.MockFactory.catalog("Time Entries", "", "Select a task assignment.")
    property var    selectedTimeEntryModel:     AppMock.MockFactory.detail()
    property string selectedEntryId:            ""
    property var    periodOptions:              []
    property string selectedPeriodStart:        ""

    property var    collaborationCommentsModel: AppMock.MockFactory.catalog("Collaboration", "", "Select a task.")
    property var    collaborationPresenceModel: AppMock.MockFactory.catalog("Active Presence", "", "Select a task.")
    property string selectedTaskId: ""

    // ── Signals ───────────────────────────────────────────────────────
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

    // ── Private helpers ───────────────────────────────────────────────
    readonly property real _progressValue: {
        const s = root.taskDetail.state || {}
        return parseFloat(s.percentComplete || "0") / 100.0
    }
    readonly property string _progressLabel: {
        const s = root.taskDetail.state || {}
        return String(s.percentCompleteLabel || "")
    }
    readonly property bool _hasTask: String(root.taskDetail.id || "").length > 0

    implicitHeight: _mainCol.implicitHeight

    Column {
        id: _mainCol
        width: parent ? parent.width : 0
        spacing: 0

        // ── Compact summary strip ─────────────────────────────────────
        Rectangle {
            width:   parent.width
            height:  40
            color:   Theme.AppTheme.surfaceAlt
            visible: root._hasTask

            Rectangle {
                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                height: 1; color: Theme.AppTheme.divider
            }

            RowLayout {
                anchors.fill:        parent
                anchors.leftMargin:  Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.StatusChip {
                    visible: String(root.taskDetail.statusLabel || "").length > 0
                    status:  root.taskDetail.statusLabel || ""
                }

                RowLayout {
                    visible: root._progressValue > 0
                    spacing: Theme.AppTheme.spacingXs

                    AppWidgets.ProgressBar {
                        implicitWidth: 90
                        value: root._progressValue
                    }

                    Label {
                        text:           root._progressLabel
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                }

                Rectangle {
                    width: 1; height: 14
                    color:   Theme.AppTheme.divider
                    visible: String(root.taskDetail.subtitle || "").length > 0
                        && (String(root.taskDetail.statusLabel || "").length > 0 || root._progressValue > 0)
                }

                Label {
                    Layout.fillWidth: true
                    text:           root.taskDetail.subtitle || ""
                    color:          Theme.AppTheme.textSecondary
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    elide:          Text.ElideRight
                    visible:        text.length > 0
                }
            }
        }

        // ── Section 0: Details ────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 0; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Details" }

        Item {
            width:          parent.width
            implicitHeight: _detailsContent.implicitHeight + Theme.AppTheme.spacingMd * 2

            ColumnLayout {
                id: _detailsContent
                anchors.top:         parent.top
                anchors.left:        parent.left
                anchors.right:       parent.right
                anchors.topMargin:   Theme.AppTheme.spacingMd
                anchors.leftMargin:  Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingMd

                // Empty state when no task selected
                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: !root._hasTask
                        && String(root.taskDetail.emptyState || "").length > 0
                    title:   root.taskDetail.emptyState || ""
                }

                // Description
                Label {
                    Layout.fillWidth: true
                    visible:        root._hasTask
                        && String(root.taskDetail.description || "").length > 0
                    text:           root.taskDetail.description || ""
                    color:          Theme.AppTheme.textPrimary
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    wrapMode:       Text.WordWrap
                }

                // ── Compact metadata grid (2 columns) ─────────────────
                GridLayout {
                    Layout.fillWidth: true
                    visible:  root._hasTask && (root.taskDetail.fields || []).length > 0
                    columns:  2
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing:    Theme.AppTheme.spacingMd

                    Repeater {
                        model: root.taskDetail.fields || []

                        delegate: ColumnLayout {
                            id: _field
                            required property var modelData

                            Layout.fillWidth: true
                            spacing: 2

                            Label {
                                text:           String(_field.modelData.label || "")
                                color:          Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold:      true
                            }

                            Label {
                                Layout.fillWidth: true
                                text:           String(_field.modelData.value || "—")
                                color:          Theme.AppTheme.textPrimary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                elide:          Text.ElideRight
                            }

                            Label {
                                Layout.fillWidth: true
                                visible:        String(_field.modelData.supportingText || "").length > 0
                                text:           String(_field.modelData.supportingText || "")
                                color:          Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                elide:          Text.ElideRight
                            }
                        }
                    }
                }

                // Grid bottom divider
                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color:  Theme.AppTheme.divider
                    visible: root._hasTask && (root.taskDetail.fields || []).length > 0
                }
            }
        }

        // ── Section 1: Assignments ────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 1; detailPage: root.detailPage }

        Item {
            width:          parent.width
            implicitHeight: _assignmentsInner.implicitHeight

            TasksAssignmentsSection {
                id: _assignmentsInner
                anchors.left:  parent.left
                anchors.right: parent.right
                anchors.top:   parent.top

                assignmentsModel:     root.assignmentsModel
                selectedAssignmentId: root.selectedAssignmentId
                isBusy:               root.isBusy
                canCreate:            root._hasTask && root.assignmentOptions.length > 0

                onCreateRequested:           root.createAssignmentRequested()
                onAssignmentSelected: function(id) { root.assignmentSelected(id) }
                onEditAllocationRequested: function(data) { root.editAllocationRequested(data) }
                onSetHoursRequested: function(data)       { root.setHoursRequested(data) }
                onDeleteRequested: function(data)         { root.deleteAssignmentRequested(data) }
            }
        }

        // ── Section 2: Dependencies ───────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 2; detailPage: root.detailPage }

        Item {
            width:          parent.width
            implicitHeight: _dependenciesInner.implicitHeight

            TasksDependenciesSection {
                id: _dependenciesInner
                anchors.left:  parent.left
                anchors.right: parent.right
                anchors.top:   parent.top

                dependenciesModel: root.dependenciesModel
                isBusy:            root.isBusy
                canCreate:         root._hasTask && root.dependencyTaskOptions.length > 0

                onCreateRequested:           root.createDependencyRequested()
                onDeleteRequested: function(data) { root.deleteDependencyRequested(data) }
            }
        }

        // ── Section 3: Time ───────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 3; detailPage: root.detailPage }

        Item {
            width:          parent.width
            implicitHeight: _timeInner.implicitHeight

            TasksTimeEntriesSection {
                id: _timeInner
                anchors.left:  parent.left
                anchors.right: parent.right
                anchors.top:   parent.top

                assignmentSummary:   root.timeAssignmentSummaryModel
                periodOptions:       root.periodOptions
                selectedPeriodStart: root.selectedPeriodStart
                entriesModel:        root.timeEntriesModel
                selectedEntryDetail: root.selectedTimeEntryModel
                selectedEntryId:     root.selectedEntryId
                isBusy:              root.isBusy

                onPeriodChanged: function(p) { root.periodChanged(p) }
                onEntrySelected: function(id) { root.entrySelected(id) }
                onAddRequested:    function(payload) { root.timeAddRequested(payload) }
                onUpdateRequested: function(payload) { root.timeUpdateRequested(payload) }
                onDeleteRequested: function(id)      { root.timeDeleteRequested(id) }
                onSubmitRequested: function(payload) { root.timeSubmitRequested(payload) }
                onLockRequested:   function(payload) { root.timeLockRequested(payload) }
                onUnlockRequested: function(payload) { root.timeUnlockRequested(payload) }
            }
        }

        // ── Section 4: Activity ───────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 4; detailPage: root.detailPage }

        Item {
            width:          parent.width
            implicitHeight: _collaborationInner.implicitHeight

            TasksCollaborationSection {
                id: _collaborationInner
                anchors.left:  parent.left
                anchors.right: parent.right
                anchors.top:   parent.top

                commentsModel:  root.collaborationCommentsModel
                presenceModel:  root.collaborationPresenceModel
                selectedTaskId: root.selectedTaskId
                isBusy:         root.isBusy
                canCompose:     root._hasTask

                onComposeRequested:            root.composeRequested()
                onMarkReadRequested: function(id) { root.markReadRequested(id) }
                onRefreshRequested:            root.collaborationRefreshRequested()
            }
        }

        // Bottom padding
        Item { width: parent.width; height: Theme.AppTheme.spacingLg }
    }
}
