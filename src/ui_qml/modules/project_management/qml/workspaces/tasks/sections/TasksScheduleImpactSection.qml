pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Phase (Task Detail -> Schedule Impact): answers "is this task critical,
// how much flexibility does it have, what drives its dates, are there
// conflicts, and what would happen if it moved" -- current-state facts
// are always visible; the downstream what-if simulation only runs when
// the user explicitly clicks Preview Impact (never automatically). QML
// performs zero schedule calculation -- every fact here comes from the
// canonical run_cpm-backed backend.
Item {
    id: root

    property var scheduleImpactModel: ({
        "isAvailable": false, "taskId": "", "unavailableReason": "", "currentStartLabel": "--", "currentFinishLabel": "--",
        "isCritical": false, "totalFloatDays": null, "freeFloatDays": null,
        "baselineFinishLabel": "--", "scheduleVarianceDays": null, "scheduleVarianceLabel": "",
        "drivers": [], "conflicts": [], "actualVariances": [],
        "downstream": { "directSuccessorCount": 0, "downstreamTaskCount": 0, "downstreamMilestoneCount": 0, "criticalDownstreamCount": 0 }
    })
    property var scheduleImpactPreviewModel: ({})
    property var sectionErrors: ({})
    property bool isBusy: false

    signal previewRequested(int delayWorkingDays)
    signal openTaskRequested(string taskId)

    property int _delayWorkingDays: 1
    property bool _isPreviewing: false
    property string _selectedAffectedTaskId: ""

    readonly property var _m: root.scheduleImpactModel || {}
    readonly property var _preview: root.scheduleImpactPreviewModel || {}
    readonly property string _unavailableMessage: {
        const reason = String(root._m.unavailableReason || "")
        if (reason === "summary_task")
            return "This task has sub-tasks. Schedule impact analysis applies to individual (leaf) tasks, not summary tasks -- select one of its sub-tasks instead."
        if (reason === "not_found")
            return "This task could not be found in the current project schedule."
        if (reason === "no_computed_date")
            return "This task needs a start date, or an incoming dependency, before a schedule position can be computed."
        if (reason === "service_not_configured")
            return "Schedule impact analysis is not connected in this app session (the scheduling service was not wired at startup). This affects every task, not just this one -- restart the app, and if it persists, this needs backend investigation."
        if (reason === "error")
            return "Schedule impact analysis failed unexpectedly for this task. Check the application log for details."
        if (reason === "missing_task_or_project_id")
            return "No task is selected."
        return "This task needs a computed start date and a connected scheduling service."
    }
    readonly property bool _hasPreview: root._preview.isAvailable === true
    readonly property bool _previewBlockedByDeadline: root._preview.blockedByDeadline === true
    readonly property var _affectedRows: root._hasPreview ? (root._preview.rows || []) : []

    function _selectedRow() {
        const rows = root._affectedRows
        for (let i = 0; i < rows.length; i++) {
            if (String(rows[i].taskId || "") === root._selectedAffectedTaskId) return rows[i]
        }
        return null
    }
    readonly property var _selectedRowData: root._selectedRow()

    // Task switch (a new scheduleImpactModel identity) must drop preview
    // state, selection, and the previewing flag before the new task's
    // facts render -- no stale result may remain visible.
    onScheduleImpactModelChanged: {
        root._delayWorkingDays = 1
        root._isPreviewing = false
        if (root._selectedAffectedTaskId !== "") {
            root._selectedAffectedTaskId = ""
        }
    }

    function runPreview() {
        root._isPreviewing = true
        root._selectedAffectedTaskId = ""
        root.previewRequested(root._delayWorkingDays)
        Qt.callLater(function() { root._isPreviewing = false })
    }

    implicitHeight: _col.implicitHeight

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Schedule Impact"
            subtitle: "Understand how this task affects the surrounding schedule."
            busy: root.isBusy
            actions: []
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.sectionErrors["scheduleImpact"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["scheduleImpact"] || "")
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            Layout.topMargin: Theme.AppTheme.spacingLg
            Layout.bottomMargin: Theme.AppTheme.spacingLg
            visible: !root.isBusy && root._m.isAvailable !== true
            title: "Schedule impact analysis not available."
            message: root._unavailableMessage
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd
            visible: root._m.isAvailable === true

            // ── Schedule position (compact facts, no oversized KPI cards) ──
            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 640 ? 4 : 2
                columnSpacing: Theme.AppTheme.spacingLg
                rowSpacing: Theme.AppTheme.spacingSm

                ColumnLayout {
                    spacing: 2
                    AppControls.Label {
                        text: "Current Finish"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                    AppControls.Label {
                        text: String(root._m.currentFinishLabel || "--")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                    }
                }
                ColumnLayout {
                    spacing: 2
                    AppControls.Label {
                        text: "Critical Path"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                    AppWidgets.StatusChip {
                        status: root._m.isCritical === true ? "Critical" : "Not critical"
                    }
                }
                ColumnLayout {
                    spacing: 2
                    AppControls.Label {
                        text: "Total Float"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                    AppControls.Label {
                        text: root._m.totalFloatDays !== null && root._m.totalFloatDays !== undefined
                            ? (String(root._m.totalFloatDays) + " working day" + (root._m.totalFloatDays === 1 ? "" : "s"))
                            : "--"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                    }
                }
                ColumnLayout {
                    spacing: 2
                    AppControls.Label {
                        text: "Downstream Tasks"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                    AppControls.Label {
                        text: String(root._m.downstream ? root._m.downstream.downstreamTaskCount : 0)
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingLg
                visible: (root._m.freeFloatDays !== null && root._m.freeFloatDays !== undefined)
                    || String(root._m.baselineFinishLabel || "--") !== "--"

                AppControls.Label {
                    visible: root._m.freeFloatDays !== null && root._m.freeFloatDays !== undefined
                    text: "Free Float: " + String(root._m.freeFloatDays) + " working days"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    visible: String(root._m.baselineFinishLabel || "--") !== "--"
                    text: "Baseline Finish: " + String(root._m.baselineFinishLabel || "--")
                        + (root._m.scheduleVarianceLabel ? "  ·  Variance " + String(root._m.scheduleVarianceLabel) : "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.AppTheme.borderWidthThin
                color: Theme.AppTheme.divider
            }

            // ── Schedule drivers ─────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "SCHEDULE DRIVERS"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: (root._m.drivers || []).length === 0
                    text: "No dependency, constraint, or actual-date driver is currently set for this task."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: root._m.drivers || []
                    delegate: RowLayout {
                        id: _driverRow
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm
                        AppControls.Label {
                            text: String(_driverRow.modelData.label || "")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_driverRow.modelData.detail || "")
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                        }
                    }
                }

                Repeater {
                    model: root._m.conflicts || []
                    delegate: AppWidgets.InlineMessage {
                        id: _conflictMsg
                        required property var modelData
                        Layout.fillWidth: true
                        tone: "danger"
                        message: "⚠ Hard constraint (" + String(_conflictMsg.modelData.constraintType || "")
                            + " · " + String(_conflictMsg.modelData.constraintDateLabel || "")
                            + ") conflicts with the predecessor relationship, which requires "
                            + String(_conflictMsg.modelData.dependencyRequiredDateLabel || "") + "."
                    }
                }

                Repeater {
                    model: root._m.actualVariances || []
                    delegate: AppWidgets.InlineMessage {
                        id: _varianceMsg
                        required property var modelData
                        Layout.fillWidth: true
                        tone: "warning"
                        message: "⚠ Task " + String(_varianceMsg.modelData.direction || "")
                            + " actual (" + String(_varianceMsg.modelData.actualDateLabel || "") + ") is before what its "
                            + "dependency required (" + String(_varianceMsg.modelData.dependencyRequiredDateLabel || "") + ")."
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.AppTheme.borderWidthThin
                color: Theme.AppTheme.divider
            }

            // ── What-if analysis ─────────────────────────────────────────
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.Label {
                    text: "Delay by"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                }
                AppControls.TextField {
                    id: _delayField
                    Layout.preferredWidth: 60
                    text: String(root._delayWorkingDays)
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    onTextChanged: {
                        const parsed = parseInt(text || "1", 10)
                        root._delayWorkingDays = isNaN(parsed) ? 1 : Math.max(1, parsed)
                    }
                }
                AppControls.Label {
                    text: "working day(s)"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                }
                Item { Layout.fillWidth: true }
                AppControls.PrimaryButton {
                    text: "Preview Impact"
                    iconName: "refresh"
                    enabled: !root.isBusy && !root._isPreviewing
                    onClicked: root.runPreview()
                }
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: root._isPreviewing
                text: "Analyzing schedule impact…"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: "This preview does not modify the project schedule."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
            }

            // ── Impact result ────────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm
                visible: root._hasPreview && !root._isPreviewing

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Theme.AppTheme.borderWidthThin
                    color: Theme.AppTheme.divider
                }

                AppControls.Label {
                    text: "IMPACT SUMMARY"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root._previewBlockedByDeadline
                    tone: "danger"
                    message: String(root._preview.blockedReason || "This proposed delay would breach the task's deadline.")
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root._preview.requiresApproval === true
                    tone: "warning"
                    message: "A change of this magnitude would require baseline approval."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root._preview.criticalPathChanged === true
                    tone: "warning"
                    message: "⚠ Critical path changed"
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: (root._preview.conflictCount || 0) > 0
                    tone: "danger"
                    message: String(root._preview.conflictCount || 0) + " constraint conflict(s) under the proposed change."
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: !root._previewBlockedByDeadline
                    text: String(root._preview.summary || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: root._affectedRows.length === 0 && !root._previewBlockedByDeadline
                    title: "No downstream schedule changes were detected."
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: root._affectedRows.length > 0

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(160, Math.min(60 + root._affectedRows.length * 40, 360))

                        AppWidgets.DataTable {
                            anchors.fill: parent
                            columns: [
                                { key: "taskName",           label: "Task",             flex: 3, sortable: false },
                                { key: "projectedFinishLabel", label: "Projected Date", flex: 2, sortable: false },
                                { key: "finishShiftLabel",   label: "Shift",            flex: 1, sortable: false, minWidth: 70 },
                                { key: "statusLabel",        label: "Critical",         flex: 0, minWidth: 90, type: "status" }
                            ]
                            rows: root._affectedRows.map(function(row) {
                                return {
                                    "id": row.taskId,
                                    "taskName": row.taskName,
                                    "projectedFinishLabel": row.projectedFinishLabel,
                                    "finishShiftLabel": row.finishShiftLabel,
                                    "statusLabel": row.isMilestone ? "Milestone" : (row.isCritical ? "Critical" : "Non-critical")
                                }
                            })
                            selectedRowId: root._selectedAffectedTaskId

                            onRowSelected: function(rowId) { root._selectedAffectedTaskId = rowId }
                            onRowActivated: function(rowId) { root._selectedAffectedTaskId = rowId }
                        }
                    }

                    AppWidgets.InspectorPanel {
                        id: _affectedInspector
                        Layout.preferredWidth: Theme.AppTheme.inspectorWidth
                        Layout.fillHeight: true
                        visible: root._selectedRowData !== null
                        title: root._selectedRowData ? String(root._selectedRowData.taskName || "") : ""
                        statusLabel: root._selectedRowData
                            ? (root._selectedRowData.isMilestone ? "Milestone" : (root._selectedRowData.isCritical ? "Critical" : "Non-critical"))
                            : ""
                        sections: root._selectedRowData ? [
                            { "label": "Current Date", "value": String(root._selectedRowData.currentFinishLabel || "--") },
                            { "label": "Projected Date", "value": String(root._selectedRowData.projectedFinishLabel || "--") },
                            { "label": "Shift", "value": String(root._selectedRowData.finishShiftLabel || "") }
                        ] : []
                        showEditAction: false
                        showSecondaryAction: false

                        onCloseRequested: root._selectedAffectedTaskId = ""

                        AppControls.SecondaryButton {
                            Layout.fillWidth: true
                            text: "Open Task"
                            iconName: "open"
                            enabled: root._selectedRowData !== null
                            onClicked: {
                                if (root._selectedRowData) root.openTaskRequested(String(root._selectedRowData.taskId || ""))
                            }
                        }
                    }
                }
            }
        }
    }
}
