pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    // Every valid TaskAssignment for this task (docs §44 Time redesign §13)
    // -- Log Time's assignment choice is local to this component, entirely
    // independent of whatever is selected in Task Detail -> Assignment.
    property var assignmentOptions: []
    // Task-scoped summary (docs §44), used only to look up the chosen
    // assignment's Planned/Logged/Remaining context -- never recalculated
    // here.
    property var taskTimeSummary: ({ "hasSummary": false })
    property var entryState: ({})
    property bool isBusy: false

    signal addRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string entryId)
    signal cancelEditRequested()

    property string _selectedAssignmentId: ""

    readonly property var _entryState: root.entryState || {}
    readonly property bool _hasEntry: Boolean(root._entryState.entryId)
    readonly property var _breakdown: (root.taskTimeSummary && root.taskTimeSummary.resourceBreakdown) || []
    readonly property var _selectedContext: {
        const id = root._selectedAssignmentId
        for (let i = 0; i < root._breakdown.length; i += 1) {
            if (String(root._breakdown[i].assignmentId || "") === id)
                return root._breakdown[i]
        }
        return null
    }
    readonly property bool _hasAssignment: root._selectedAssignmentId.length > 0

    // §14: exactly one valid assignment -> preselect it; more than one ->
    // require explicit selection (no guessed default).
    function _defaultAssignmentId() {
        return root.assignmentOptions.length === 1
            ? String(root.assignmentOptions[0].value || "")
            : ""
    }

    function _applyEntryStateToAssignment() {
        if (root._entryState.assignmentId) {
            root._selectedAssignmentId = String(root._entryState.assignmentId)
        } else if (!root._selectedAssignmentId) {
            root._selectedAssignmentId = root._defaultAssignmentId()
        }
    }

    function _syncEditorFields() {
        if (!_dateField || !_hoursField || !_noteArea)
            return
        root._applyEntryStateToAssignment()
        if (root._entryState.entryId) {
            _dateField.text = String(root._entryState.entryDate || "")
            _hoursField.text = String(root._entryState.hours || "")
            _noteArea.text = String(root._entryState.note || "")
        } else {
            _dateField.text = ""
            _hoursField.text = ""
            _noteArea.text = ""
        }
    }

    function resetForCreate() {
        // Retain a valid assignment to make repeated logging efficient, but
        // clear all entry-specific values after a successful mutation.
        let assignmentStillAvailable = false
        for (let i = 0; i < root.assignmentOptions.length; i += 1) {
            if (String(root.assignmentOptions[i].value || "") === root._selectedAssignmentId) {
                assignmentStillAvailable = true
                break
            }
        }
        if (!assignmentStillAvailable) {
            root._selectedAssignmentId = root._defaultAssignmentId()
        }
        _dateField.text = ""
        _hoursField.text = ""
        _noteArea.text = ""
    }

    onEntryStateChanged: Qt.callLater(root._syncEditorFields)
    onAssignmentOptionsChanged: {
        if (!root._selectedAssignmentId) {
            root._selectedAssignmentId = root._defaultAssignmentId()
        }
    }
    Component.onCompleted: root._syncEditorFields()

    Layout.fillWidth: true
    implicitHeight: _captureEditorColumn.implicitHeight + Theme.AppTheme.marginMd * 2
    radius: Theme.AppTheme.radiusMd
    color: Theme.AppTheme.surfaceRaised
    border.color: Theme.AppTheme.subtleBorder
    border.width: 1

    ColumnLayout {
        id: _captureEditorColumn
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                AppControls.Label {
                    Layout.fillWidth: true
                    text: root._hasEntry ? "Edit Time Entry" : "Log Time"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: root._hasEntry
                        ? "Update the selected recorded-work entry."
                        : "Record actual work performed against this task."
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                implicitWidth: _entryModeLabel.implicitWidth + Theme.AppTheme.spacingMd * 2
                implicitHeight: Theme.AppTheme.toolbarHeight
                radius: Theme.AppTheme.radiusSm
                color: root._hasEntry ? Theme.AppTheme.accentSoft : Theme.AppTheme.surfaceAlt
                border.color: Theme.AppTheme.subtleBorder
                border.width: 1

                AppControls.Label {
                    id: _entryModeLabel
                    anchors.centerIn: parent
                    text: root._hasEntry
                        ? "Editing entry — recorded by " + String(root._entryState.authorUsername || "unknown")
                        : "New entry"
                    color: root._hasEntry ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            AppControls.Label {
                text: "Assignment"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
            }

            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.assignmentOptions
                textRole: "label"
                enabled: !root.isBusy && !root._hasEntry
                currentIndex: {
                    const options = root.assignmentOptions
                    for (let i = 0; i < options.length; i += 1) {
                        if (String(options[i].value || "") === root._selectedAssignmentId)
                            return i
                    }
                    return -1
                }
                onActivated: function(index) {
                    const option = root.assignmentOptions[index]
                    if (option) root._selectedAssignmentId = String(option.value || "")
                }
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: root.assignmentOptions.length === 0
                text: "No resources are assigned to this task."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode: Text.WordWrap
            }
        }

        Rectangle {
            Layout.fillWidth: true
            visible: root._selectedContext !== null
            implicitHeight: _contextRow.implicitHeight + Theme.AppTheme.spacingMd * 2
            radius: Theme.AppTheme.radiusSm
            color: Theme.AppTheme.surfaceAlt
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1

            RowLayout {
                id: _contextRow
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                AppControls.Label {
                    Layout.fillWidth: true
                    text: root._selectedContext
                        ? String(root._selectedContext.resourceName || "")
                        : ""
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                AppControls.Label {
                    text: "Planned " + (root._selectedContext ? String(root._selectedContext.plannedHoursLabel || "") : "")
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }
                AppControls.Label {
                    text: "Logged " + (root._selectedContext ? String(root._selectedContext.actualHoursLabel || "") : "")
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }
                AppControls.Label {
                    text: (root._selectedContext && root._selectedContext.hasOverrun ? "Overrun " : "Remaining ")
                        + (root._selectedContext
                            ? String((root._selectedContext.hasOverrun
                                ? root._selectedContext.overrunHoursLabel
                                : root._selectedContext.remainingHoursLabel) || "")
                            : "")
                    color: (root._selectedContext && root._selectedContext.hasOverrun) ? Theme.AppTheme.danger : Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: root._selectedContext && root._selectedContext.hasOverrun
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width >= 760 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                AppControls.Label {
                    text: "Date"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.DateField {
                    id: _dateField
                    Layout.fillWidth: true
                    enabled: !root.isBusy && root._hasAssignment
                    placeholderText: "YYYY-MM-DD"
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                AppControls.Label {
                    text: "Hours"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.TextField {
                    id: _hoursField
                    Layout.fillWidth: true
                    enabled: !root.isBusy && root._hasAssignment
                    placeholderText: "8.00"
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            AppControls.Label {
                text: "Description"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
            }

            AppControls.TextArea {
                id: _noteArea
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                enabled: !root.isBusy && root._hasAssignment
                placeholderText: "Describe the work completed, blockers, and key deliverables for this entry."
                wrapMode: TextEdit.WordWrap
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: "Delete"
                iconName: "delete"
                danger: true
                visible: root._hasEntry
                enabled: !root.isBusy
                onClicked: _deleteConfirmation.open()
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: root._hasAssignment
                    ? "Actual work is historical -- logging beyond the planned hours is allowed and will show as an overrun."
                    : "Choose an assignment before logging time."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode: Text.WordWrap
            }

            AppControls.SecondaryButton {
                text: "Cancel"
                visible: root._hasEntry
                enabled: !root.isBusy
                onClicked: root.cancelEditRequested()
            }

            AppControls.PrimaryButton {
                text: root._hasEntry ? "Save Changes" : "Log Time"
                iconName: root._hasEntry ? "save" : "add"
                enabled: !root.isBusy
                    && root._hasAssignment
                    && _dateField.text.trim().length > 0
                    && _hoursField.text.trim().length > 0
                onClicked: {
                    if (root._hasEntry) {
                        root.updateRequested({
                            "entryId": root._entryState.entryId || "",
                            "entryDate": _dateField.text,
                            "hours": _hoursField.text,
                            "note": _noteArea.text
                        })
                    } else {
                        root.addRequested({
                            "assignmentId": root._selectedAssignmentId,
                            "entryDate": _dateField.text,
                            "hours": _hoursField.text,
                            "note": _noteArea.text
                        })
                    }
                }
            }

        }
    }

    AppControls.ConfirmationDialog {
        id: _deleteConfirmation
        title: "Delete Time Entry"
        closePolicy: Popup.CloseOnEscape
        confirmLabel: "Delete Entry"
        confirmIcon: "delete"
        confirmDanger: true
        message: "Delete the selected time entry?"
        supportingText: String(root._entryState.entryDate || "") + " - "
            + String(root._entryState.hours || "")
            + " h. The recorded work will be removed from task and timesheet totals."
        onConfirmed: root.deleteRequested(String(root._entryState.entryId || ""))
    }
}
