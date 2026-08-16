import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Register Entry"
    property var projectOptions: []
    property var typeOptions: []
    property var statusOptions: []
    property var severityOptions: []
    property var entryData: ({})
    property bool typeFieldVisible: true
    property string fixedTypeValue: "RISK"
    property var workspaceController: null
    property string entryCode: ""
    readonly property var editableProjectOptions: (root.projectOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })
    readonly property var editableTypeOptions: (root.typeOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })
    readonly property var editableStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })
    readonly property var editableSeverityOptions: (root.severityOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(var payload)

    title:        root.modeTitle
    subtitle:     "Capture the project, entry type, severity, status, and response context for this governance item."
    primaryText:  root.modeTitle.indexOf("Create") === 0 ? "Create Entry" : "Save Changes"
    primaryIcon:  root.modeTitle.indexOf("Create") === 0 ? "add" : "save"
    width: 680
    // Height is content-driven via EntityDialog (caps to window, scrolls if tall).

    onOpened: root.populateFromEntry()
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function indexForValue(options, targetValue) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromEntry() {
        var state = root.entryData && root.entryData.state ? root.entryData.state : (root.entryData || {})
        projectCombo.currentIndex = root.indexForValue(root.editableProjectOptions, state.projectId || "")
        typeCombo.currentIndex = root.indexForValue(root.editableTypeOptions, state.type || root.fixedTypeValue)
        statusCombo.currentIndex = root.indexForValue(root.editableStatusOptions, state.status || "OPEN")
        severityCombo.currentIndex = root.indexForValue(root.editableSeverityOptions, state.severity || "MEDIUM")
        root.entryCode = String(state.entryCode || "")
        titleField.text = String(state.title || "")
        ownerField.text = String(state.ownerName || "")
        dueDateField.text = String(state.dueDate || "")
        descriptionField.text = String(state.description || "")
        impactField.text = String(state.impactSummary || "")
        responseField.text = String(state.responsePlan || "")
        root.errorMessage = ""
    }

    function buildPayload() {
        var typeOption = root.editableTypeOptions[typeCombo.currentIndex] || { "value": root.fixedTypeValue }
        var statusOption = root.editableStatusOptions[statusCombo.currentIndex] || { "value": "OPEN" }
        var severityOption = root.editableSeverityOptions[severityCombo.currentIndex] || { "value": "MEDIUM" }
        var projectOption = root.editableProjectOptions[projectCombo.currentIndex] || { "value": "" }
        return {
            "projectId": String(projectOption.value || ""),
            "entryCode": root.entryCode,
            "entryType": root.typeFieldVisible ? String(typeOption.value || root.fixedTypeValue) : root.fixedTypeValue,
            "title": titleField.text,
            "status": String(statusOption.value || "OPEN"),
            "severity": String(severityOption.value || "MEDIUM"),
            "ownerName": ownerField.text,
            "dueDate": dueDateField.text,
            "description": descriptionField.text,
            "impactSummary": impactField.text,
            "responsePlan": responseField.text
        }
    }

    function submitDialog() {
        if (root.editableProjectOptions.length === 0) {
            root.errorMessage = "Create a project before adding a register entry."
            return
        }
        if (String((root.editableProjectOptions[projectCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a project before saving."
            return
        }
        if (titleField.text.trim().length === 0) {
            root.errorMessage = "Register title is required."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 600 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.CodeFieldRow {
            Layout.columnSpan: parent.columns
            Layout.fillWidth: true
            label: "Register code"
            value: root.entryCode
            placeholderText: "Auto-generated if empty"
            required: true
            generateVisible: true
            busy: root.workspaceController ? root.workspaceController.isBusy : false
            onValueEdited: function(code) { root.entryCode = code }
            onGenerateRequested: {
                if (root.workspaceController) {
                    const suggested = root.workspaceController.generateEntityCode("register", root.buildPayload())
                    if (suggested && suggested.length > 0) {
                        root.entryCode = suggested
                    }
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Project"
            required: true
            AppControls.ComboBox {
                id: projectCombo
                Layout.fillWidth: true
                model: root.editableProjectOptions
                textRole: "label"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: root.typeFieldVisible
            label: "Entry type"
            AppControls.ComboBox {
                id: typeCombo
                visible: root.typeFieldVisible
                Layout.fillWidth: true
                model: root.editableTypeOptions
                textRole: "label"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Title"
            required: true
            AppControls.TextField {
                id: titleField
                Layout.fillWidth: true
                placeholderText: root.typeFieldVisible ? "Critical supplier dependency" : "Late switchgear delivery"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Severity"
            AppControls.ComboBox {
                id: severityCombo
                Layout.fillWidth: true
                model: root.editableSeverityOptions
                textRole: "label"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Status"
            AppControls.ComboBox {
                id: statusCombo
                Layout.fillWidth: true
                model: root.editableStatusOptions
                textRole: "label"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Owner"
            AppControls.TextField {
                id: ownerField
                Layout.fillWidth: true
                placeholderText: "PM Lead"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Due date"
            AppControls.DateField {
                id: dueDateField
                Layout.fillWidth: true
                placeholderText: "YYYY-MM-DD"
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Description"
        AppControls.TextArea {
            id: descriptionField
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            placeholderText: "Describe the trigger, scope, or context behind this entry."
            wrapMode: TextEdit.WordWrap
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Impact summary"
        AppControls.TextArea {
            id: impactField
            Layout.fillWidth: true
            Layout.preferredHeight: 110
            placeholderText: "Summarize delivery, cost, or schedule impact."
            wrapMode: TextEdit.WordWrap
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Response plan"
        AppControls.TextArea {
            id: responseField
            Layout.fillWidth: true
            Layout.preferredHeight: 130
            placeholderText: "Capture mitigation, action owner, and next review step."
            wrapMode: TextEdit.WordWrap
        }
    }
}
