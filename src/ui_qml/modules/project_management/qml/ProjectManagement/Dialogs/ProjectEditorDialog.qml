import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Project"
    property var statusOptions: []
    property var projectData: ({})
    property string validationMessage: ""
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(var payload)

    title:        root.modeTitle
    subtitle:     root.modeTitle === "Create Project"
        ? "Set up a project record and delivery baseline context."
        : "Update the project profile, schedule dates, or status."
    errorMessage: root.validationMessage
    primaryText:  root.modeTitle === "Create Project" ? "Create Project" : "Save Changes"
    primaryIcon:  root.modeTitle === "Create Project" ? "add" : "save"
    width: 560

    onOpened:   root.populateFromProject()
    onAccepted: root.submitDialog()
    onRejected: root.close()

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
        root.validationMessage = ""
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

    function submitDialog() {
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "Project name is required."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 520 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Project name"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Plant Upgrade" }

        AppControls.Label { text: "Status"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.workflowStatusOptions; textRole: "label" }

        AppControls.Label { text: "Client"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: clientNameField; Layout.fillWidth: true; placeholderText: "Contoso Manufacturing" }

        AppControls.Label { text: "Client contact"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: clientContactField; Layout.fillWidth: true; placeholderText: "client@example.com" }

        AppControls.Label { text: "Planned budget"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: plannedBudgetField; Layout.fillWidth: true; inputMethodHints: Qt.ImhFormattedNumbersOnly; placeholderText: "250000.00" }

        AppControls.Label { text: "Currency"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: currencyField; Layout.fillWidth: true; placeholderText: "EUR" }

        AppControls.Label { text: "Start date"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.DateField { id: startDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }

        AppControls.Label { text: "Finish date"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.DateField { id: endDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }
    }

    AppControls.Label {
        Layout.fillWidth: true
        text: "Description"
        color: Theme.AppTheme.textPrimary
        font.family: Theme.AppTheme.fontFamily
    }

    AppControls.TextArea {
        id: descriptionField
        Layout.fillWidth: true
        Layout.preferredHeight: 140
        placeholderText: "Scope, delivery context, and stakeholder notes."
        wrapMode: TextEdit.WordWrap
    }
}
