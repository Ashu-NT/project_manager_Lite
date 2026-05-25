pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Mock 1.0 as AppMock
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

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

    property var dependenciesModel:     AppMock.MockFactory.catalog("Dependencies", "", "Select a task.")
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

    // ── Private ───────────────────────────────────────────────────────
    readonly property real   _progressValue: {
        const s = root.taskDetail.state || {}
        return parseFloat(s.percentComplete || "0") / 100.0
    }
    readonly property string _progressLabel: {
        const s = root.taskDetail.state || {}
        return String(s.percentCompleteLabel || "")
    }
    readonly property bool _hasTask: String(root.taskDetail.id || "").length > 0

    // Active section index from the parent detail page (0 = Details by default)
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0

    // Dynamic implicitHeight — only the active section contributes
    implicitHeight: (_summaryStrip.visible ? _summaryStrip.height : 0)
        + _activeSectionH
        + Theme.AppTheme.spacingLg

    readonly property int _activeSectionH: {
        const i = root._idx
        if (i === 0) return _sec0.implicitHeight
        if (i === 1) return _sec1.implicitHeight
        if (i === 2) return _sec2.implicitHeight
        if (i === 3) return _sec3.implicitHeight
        return _sec4.implicitHeight
    }

    // ── Summary strip (always visible when a task is open) ────────────
    Rectangle {
        id: _summaryStrip
        anchors.top:   parent.top
        anchors.left:  parent.left
        anchors.right: parent.right
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

                AppControls.Label {
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
            }

            AppControls.Label {
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

    // ── Section container — all sections stacked at the same origin ───
    // Only the active section is visible; all others have height 0.
    Item {
        id: _sectionArea
        anchors.top:   _summaryStrip.visible ? _summaryStrip.bottom : parent.top
        anchors.left:  parent.left
        anchors.right: parent.right
        height: root._activeSectionH

        // ── Section 0: Details ────────────────────────────────────────
        Item {
            id: _sec0
            visible: root._idx === 0
            width:          parent.width
            implicitHeight: _detailsCol.implicitHeight + Theme.AppTheme.spacingMd * 2

            ColumnLayout {
                id: _detailsCol
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
                AppControls.Label {
                    Layout.fillWidth: true
                    visible:        root._hasTask
                        && String(root.taskDetail.description || "").length > 0
                    text:           root.taskDetail.description || ""
                    color:          Theme.AppTheme.textPrimary
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    wrapMode:       Text.WordWrap
                }

                // ── Compact 2-column metadata grid ────────────────────
                GridLayout {
                    Layout.fillWidth: true
                    visible:       root._hasTask && (root.taskDetail.fields || []).length > 0
                    columns:       2
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing:    Theme.AppTheme.spacingMd

                    Repeater {
                        model: root.taskDetail.fields || []

                        delegate: ColumnLayout {
                            id: _field
                            required property var modelData

                            Layout.fillWidth: true
                            spacing: 2

                            AppControls.Label {
                                text:           String(_field.modelData.label || "")
                                color:          Theme.AppTheme.textMuted
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold:      true
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text:           String(_field.modelData.value || "—")
                                color:          Theme.AppTheme.textPrimary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                elide:          Text.ElideRight
                            }

                            AppControls.Label {
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

                Rectangle {
                    Layout.fillWidth: true
                    height:  1
                    color:   Theme.AppTheme.divider
                    visible: root._hasTask && (root.taskDetail.fields || []).length > 0
                }
            }
        }

        // ── Section 1: Assignments ────────────────────────────────────
        Item {
            id: _sec1
            visible: root._idx === 1
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

                onCreateRequested:                  root.createAssignmentRequested()
                onAssignmentSelected: function(id)  { root.assignmentSelected(id) }
                onEditAllocationRequested: function(d) { root.editAllocationRequested(d) }
                onSetHoursRequested: function(d)    { root.setHoursRequested(d) }
                onDeleteRequested: function(d)      { root.deleteAssignmentRequested(d) }
            }
        }

        // ── Section 2: Dependencies ───────────────────────────────────
        Item {
            id: _sec2
            visible: root._idx === 2
            width:          parent.width
            implicitHeight: _depsInner.implicitHeight

            TasksDependenciesSection {
                id: _depsInner
                anchors.left:  parent.left
                anchors.right: parent.right
                anchors.top:   parent.top

                dependenciesModel: root.dependenciesModel
                isBusy:            root.isBusy
                canCreate:         root._hasTask && root.dependencyTaskOptions.length > 0

                onCreateRequested:               root.createDependencyRequested()
                onDeleteRequested: function(d) { root.deleteDependencyRequested(d) }
            }
        }

        // ── Section 3: Time ───────────────────────────────────────────
        Item {
            id: _sec3
            visible: root._idx === 3
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

                onPeriodChanged: function(p)    { root.periodChanged(p) }
                onEntrySelected: function(id)   { root.entrySelected(id) }
                onAddRequested: function(pl)    { root.timeAddRequested(pl) }
                onUpdateRequested: function(pl) { root.timeUpdateRequested(pl) }
                onDeleteRequested: function(id) { root.timeDeleteRequested(id) }
                onSubmitRequested: function(pl) { root.timeSubmitRequested(pl) }
                onLockRequested: function(pl)   { root.timeLockRequested(pl) }
                onUnlockRequested: function(pl) { root.timeUnlockRequested(pl) }
            }
        }

        // ── Section 4: Activity ───────────────────────────────────────
        Item {
            id: _sec4
            visible: root._idx === 4
            width:          parent.width
            implicitHeight: _activityInner.implicitHeight

            TasksCollaborationSection {
                id: _activityInner
                anchors.left:  parent.left
                anchors.right: parent.right
                anchors.top:   parent.top

                commentsModel:  root.collaborationCommentsModel
                presenceModel:  root.collaborationPresenceModel
                selectedTaskId: root.selectedTaskId
                isBusy:         root.isBusy
                canCompose:     root._hasTask

                onComposeRequested:              root.composeRequested()
                onMarkReadRequested: function(id) { root.markReadRequested(id) }
                onRefreshRequested:              root.collaborationRefreshRequested()
            }
        }
    }
}
