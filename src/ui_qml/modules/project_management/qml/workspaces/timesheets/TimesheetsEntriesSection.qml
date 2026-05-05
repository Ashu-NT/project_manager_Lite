import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Rectangle {
    id: root

    property var assignmentSummary: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "fields": [],
        "state": {}
    })
    property var entriesModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property var selectedEntryDetail: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "fields": [],
        "state": {}
    })
    property string selectedEntryId: ""
    property bool isBusy: false

    signal entrySelected(string entryId)
    signal addRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string entryId)
    signal submitRequested(var payload)
    signal lockRequested(var payload)
    signal unlockRequested(var payload)

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    onSelectedEntryDetailChanged: {
        var state = root.selectedEntryDetail && root.selectedEntryDetail.state ? root.selectedEntryDetail.state : {}
        if (state.entryId) {
            entryDateField.text = String(state.entryDate || "")
            hoursField.text = String(state.hours || "")
            noteArea.text = String(state.note || "")
        }
    }

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: root.assignmentSummary.title || "Assignment Period"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.assignmentSummary.subtitle || "").length > 0
            text: root.assignmentSummary.subtitle || ""
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: (root.assignmentSummary.fields || []).length === 0 && String(root.assignmentSummary.emptyState || "").length > 0
            text: root.assignmentSummary.emptyState || ""
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.assignmentSummary.fields || []

            delegate: ColumnLayout {
                id: assignmentFieldRow

                required property var modelData
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: String(assignmentFieldRow.modelData.label || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }

                Label {
                    Layout.fillWidth: true
                    text: String(assignmentFieldRow.modelData.value || "")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    visible: String(assignmentFieldRow.modelData.supportingText || "").length > 0
                    text: String(assignmentFieldRow.modelData.supportingText || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width > 760 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            TextField { id: entryDateField; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "YYYY-MM-DD" }
            TextField { id: hoursField; Layout.fillWidth: true; enabled: !root.isBusy; placeholderText: "8.00" }
        }

        TextArea {
            id: noteArea
            Layout.fillWidth: true
            Layout.preferredHeight: 96
            enabled: !root.isBusy
            placeholderText: "What work was completed during this entry?"
            wrapMode: TextEdit.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Add Entry"
                enabled: !root.isBusy && Boolean(root.assignmentSummary.state.assignmentId)
                onClicked: {
                    root.addRequested({
                        "assignmentId": root.assignmentSummary.state.assignmentId || "",
                        "entryDate": entryDateField.text,
                        "hours": hoursField.text,
                        "note": noteArea.text
                    })
                }
            }

            AppControls.PrimaryButton {
                text: "Update Entry"
                enabled: !root.isBusy && Boolean(root.selectedEntryDetail.state.entryId)
                onClicked: {
                    root.updateRequested({
                        "entryId": root.selectedEntryDetail.state.entryId || "",
                        "entryDate": entryDateField.text,
                        "hours": hoursField.text,
                        "note": noteArea.text
                    })
                }
            }

            AppControls.PrimaryButton {
                text: "Delete Entry"
                enabled: !root.isBusy && Boolean(root.selectedEntryDetail.state.entryId)
                danger: true
                onClicked: root.deleteRequested(String(root.selectedEntryDetail.state.entryId || ""))
            }
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.entriesModel.title || "Time Entries"
            subtitle: root.entriesModel.subtitle || ""
            emptyState: root.entriesModel.emptyState || ""
            items: root.entriesModel.items || []
            selectedItemId: root.selectedEntryId
            actionsEnabled: !root.isBusy

            onItemSelected: function(itemId) {
                root.entrySelected(itemId)
            }
        }

        TextArea {
            id: periodNoteArea
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            enabled: !root.isBusy
            placeholderText: "Optional submission or lock note for the selected resource period."
            wrapMode: TextEdit.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Submit Period"
                enabled: !root.isBusy && Boolean(root.assignmentSummary.state.resourceId) && Boolean(root.assignmentSummary.state.periodStart)
                onClicked: root.submitRequested({
                    "resourceId": root.assignmentSummary.state.resourceId || "",
                    "periodStart": root.assignmentSummary.state.periodStart || "",
                    "note": periodNoteArea.text
                })
            }

            AppControls.PrimaryButton {
                text: "Lock Period"
                enabled: !root.isBusy && Boolean(root.assignmentSummary.state.resourceId) && Boolean(root.assignmentSummary.state.periodStart)
                onClicked: root.lockRequested({
                    "resourceId": root.assignmentSummary.state.resourceId || "",
                    "periodStart": root.assignmentSummary.state.periodStart || "",
                    "note": periodNoteArea.text
                })
            }

            AppControls.PrimaryButton {
                text: "Unlock Period"
                enabled: !root.isBusy && Boolean(root.assignmentSummary.state.periodId)
                onClicked: root.unlockRequested({
                    "periodId": root.assignmentSummary.state.periodId || "",
                    "note": periodNoteArea.text
                })
            }
        }
    }
}
