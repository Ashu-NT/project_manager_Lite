import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Project"
    property var statusOptions: []
    property var projectData: ({})
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(var payload)

    modal: true
    width: 560
    height: Math.min(680, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 680)
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape

    function statusIndexForValue(statusValue) {
        for (let index = 0; index < root.workflowStatusOptions.length; index += 1) {
            if (String(root.workflowStatusOptions[index].value || "") === String(statusValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromProject() {
        var state = root.projectData && root.projectData.state ? root.projectData.state : (root.projectData || {})
        nameField.text = String(state.name || "")
        clientNameField.text = String(state.clientName || "")
        clientContactField.text = String(state.clientContact || "")
        plannedBudgetField.text = String(state.plannedBudget || "")
        currencyField.text = String(state.currency || "")
        startDateField.text = String(state.startDate || "")
        endDateField.text = String(state.endDate || "")
        descriptionField.text = String(state.description || "")
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "PLANNED")
    }

    function buildPayload() {
        var statusOption = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "PLANNED" }
        return {
            "name": nameField.text,
            "clientName": clientNameField.text,
            "clientContact": clientContactField.text,
            "plannedBudget": plannedBudgetField.text,
            "currency": currencyField.text,
            "startDate": startDateField.text,
            "endDate": endDateField.text,
            "description": descriptionField.text,
            "status": statusOption.value || "PLANNED"
        }
    }

    onOpened: root.populateFromProject()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
    }

    contentItem: Flickable {
        id: dialogFlickable

        contentWidth: width
        contentHeight: formLayout.implicitHeight
        clip: true

        ColumnLayout {
            id: formLayout

            width: dialogFlickable.width
            spacing: Theme.AppTheme.spacingMd

            Label {
                Layout.fillWidth: true
                text: root.modeTitle === "Create Project"
                    ? "Set up a project record and delivery baseline context."
                    : "Update the project profile, schedule dates, or status."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 520 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label {
                    text: "Project name"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: nameField

                    Layout.fillWidth: true
                    placeholderText: "Plant Upgrade"
                }

                Label {
                    text: "Status"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                ComboBox {
                    id: statusCombo

                    Layout.fillWidth: true
                    model: root.workflowStatusOptions
                    textRole: "label"
                }

                Label {
                    text: "Client"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: clientNameField

                    Layout.fillWidth: true
                    placeholderText: "Contoso Manufacturing"
                }

                Label {
                    text: "Client contact"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: clientContactField

                    Layout.fillWidth: true
                    placeholderText: "client@example.com"
                }

                Label {
                    text: "Planned budget"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: plannedBudgetField

                    Layout.fillWidth: true
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    placeholderText: "250000.00"
                }

                Label {
                    text: "Currency"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: currencyField

                    Layout.fillWidth: true
                    placeholderText: "EUR"
                }

                Label {
                    text: "Start date"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: startDateField

                    Layout.fillWidth: true
                    placeholderText: "YYYY-MM-DD"
                }

                Label {
                    text: "Finish date"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: endDateField

                    Layout.fillWidth: true
                    placeholderText: "YYYY-MM-DD"
                }
            }

            Label {
                Layout.fillWidth: true
                text: "Description"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            TextArea {
                id: descriptionField

                Layout.fillWidth: true
                Layout.preferredHeight: 140
                placeholderText: "Scope, delivery context, and stakeholder notes."
                wrapMode: TextEdit.WordWrap
            }
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item {
            Layout.fillWidth: true
        }

        Button {
            text: "Cancel"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            text: root.modeTitle === "Create Project" ? "Create Project" : "Save Changes"
            onClicked: root.submitted(root.buildPayload())
        }
    }
}
