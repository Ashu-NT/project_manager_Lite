pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var assignmentState: ({})
    property var entryState: ({})
    property bool isBusy: false

    signal addRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string entryId)

    readonly property var _state: root.assignmentState || {}
    readonly property var _entryState: root.entryState || {}
    readonly property bool _hasAssignment: Boolean(root._state.assignmentId)
    readonly property bool _hasEntry: Boolean(root._entryState.entryId)

    function _syncEditorFields() {
        if (!_dateField || !_hoursField || !_noteArea)
            return
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

    onEntryStateChanged: Qt.callLater(root._syncEditorFields)
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
                    text: "Capture Labor Entry"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Log daily hours and update the selected time entry without leaving the task workspace."
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
                    text: root._hasEntry ? "Selected entry" : "New entry"
                    color: root._hasEntry ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.AppTheme.divider
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
                text: "Labor Note"
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

            AppControls.Label {
                Layout.fillWidth: true
                text: root._hasAssignment
                    ? "Capture work against the selected assignment and period."
                    : "Choose a task assignment before logging labor."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode: Text.WordWrap
            }

            AppControls.PrimaryButton {
                text: "Add Entry"
                iconName: "add"
                enabled: !root.isBusy && root._hasAssignment
                onClicked: root.addRequested({
                    "assignmentId": root._state.assignmentId || "",
                    "entryDate": _dateField.text,
                    "hours": _hoursField.text,
                    "note": _noteArea.text
                })
            }

            AppControls.SecondaryButton {
                text: "Update"
                iconName: "edit"
                enabled: !root.isBusy && root._hasEntry
                onClicked: root.updateRequested({
                    "entryId": root._entryState.entryId || "",
                    "entryDate": _dateField.text,
                    "hours": _hoursField.text,
                    "note": _noteArea.text
                })
            }

            AppControls.SecondaryButton {
                text: "Delete"
                iconName: "delete"
                danger: true
                enabled: !root.isBusy && root._hasEntry
                onClicked: root.deleteRequested(String(root._entryState.entryId || ""))
            }
        }
    }
}

