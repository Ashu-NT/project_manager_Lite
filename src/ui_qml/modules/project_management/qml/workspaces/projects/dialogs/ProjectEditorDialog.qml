import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Project"
    property var statusOptions: []
    property var siteOptions: []
    property var departmentOptions: []
    property var projectData: ({})
    property var workspaceController: null
    property string projectCode: ""
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })
    readonly property var currencyOptions: root.workspaceController ? (root.workspaceController.currencyOptions || []) : []
    readonly property string defaultCurrencyCode: root.workspaceController ? String(root.workspaceController.defaultCurrencyCode || "XAF") : "XAF"

    signal submitted(var payload)

    title:        root.modeTitle
    subtitle:     root.modeTitle === "Create Project"
        ? "Set up a project record and delivery baseline context."
        : "Update the project profile, schedule dates, or status."
    primaryText:  root.modeTitle === "Create Project" ? "Create Project" : "Save Changes"
    primaryIcon:  root.modeTitle === "Create Project" ? "add" : "save"
    width: 680

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

    function optionIndexForValue(options, targetValue) {
        const list = options || []
        for (let index = 0; index < list.length; index += 1) {
            if (String(list[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function currencyIndexForValue(currencyValue) {
        const wanted = String(currencyValue || "").length > 0 ? String(currencyValue) : root.defaultCurrencyCode
        const list = root.currencyOptions || []
        for (let index = 0; index < list.length; index += 1) {
            if (String(list[index].value || "") === wanted) {
                return index
            }
        }
        for (let index = 0; index < list.length; index += 1) {
            if (String(list[index].value || "") === root.defaultCurrencyCode) {
                return index
            }
        }
        return 0
    }

    function populateFromProject() {
        var state = root.projectData && root.projectData.state ? root.projectData.state : (root.projectData || {})
        root.projectCode = String(state.projectCode || "")
        nameField.text = String(state.name || "")
        clientNameField.text = String(state.clientName || "")
        clientContactField.text = String(state.clientContact || "")
        currencyCombo.currentIndex = root.currencyIndexForValue(state.financialCurrencyCode || "")
        startDateField.text = String(state.startDate || "")
        endDateField.text = String(state.endDate || "")
        descriptionField.text = String(state.description || "")
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "PLANNED")
        siteCombo.currentIndex = root.optionIndexForValue(root.siteOptions, state.siteId || "")
        departmentCombo.currentIndex = root.optionIndexForValue(root.departmentOptions, state.departmentId || "")
        root.errorMessage = ""
    }

    function buildPayload() {
        var statusOption = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "PLANNED" }
        var siteOption = root.siteOptions[siteCombo.currentIndex] || { "value": "" }
        var departmentOption = root.departmentOptions[departmentCombo.currentIndex] || { "value": "" }
        var currencyOption = root.currencyOptions[currencyCombo.currentIndex] || { "value": root.defaultCurrencyCode }
        return {
            "name": nameField.text,
            "projectCode": root.projectCode,
            "clientName": clientNameField.text,
            "clientContact": clientContactField.text,
            "financialCurrencyCode": currencyOption.value || root.defaultCurrencyCode,
            "startDate": startDateField.text,
            "endDate": endDateField.text,
            "description": descriptionField.text,
            "status": statusOption.value || "PLANNED",
            "siteId": String(siteOption.value || ""),
            "departmentId": String(departmentOption.value || "")
        }
    }

    function submitDialog() {
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Project name is required."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        id: projectFormGrid
        Layout.fillWidth: true
        // Landscape-first: at the dialog's own (clamped) width, prefer 3
        // columns over letting fields stack into extra rows, so adding a
        // field grows the dialog wider rather than taller.
        columns: root.width > 640 ? 3 : root.width > 420 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.CodeFieldRow {
            Layout.columnSpan: parent.columns
            Layout.fillWidth: true
            label: "Project code"
            value: root.projectCode
            placeholderText: "Auto-generated if empty"
            required: true
            generateVisible: true
            busy: root.workspaceController ? root.workspaceController.isBusy : false
            onValueEdited: function(code) { root.projectCode = code }
            onGenerateRequested: {
                if (root.workspaceController) {
                    const suggested = root.workspaceController.generateEntityCode("project", root.buildPayload())
                    if (suggested && suggested.length > 0) {
                        root.projectCode = suggested
                    }
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Project name"
            required: true
            AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Plant Upgrade" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Status"
            AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.workflowStatusOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Site"
            AppControls.ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.siteOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Department"
            AppControls.ComboBox { id: departmentCombo; Layout.fillWidth: true; model: root.departmentOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Client"
            AppControls.TextField { id: clientNameField; Layout.fillWidth: true; placeholderText: "Contoso Manufacturing" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Client contact"
            AppControls.TextField { id: clientContactField; Layout.fillWidth: true; placeholderText: "client@example.com" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: root.modeTitle === "Create Project"
            label: "Financial currency"
            AppControls.ComboBox { id: currencyCombo; Layout.fillWidth: true; model: root.currencyOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Start date"
            AppControls.DateField { id: startDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" ; popupBoundaryItem: projectFormGrid }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Finish date"
            AppControls.DateField { id: endDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD"; popupBoundaryItem: projectFormGrid }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Description"
        AppControls.TextArea {
            id: descriptionField
            Layout.fillWidth: true
            Layout.preferredHeight: 140
            placeholderText: "Scope, delivery context, and stakeholder notes."
            wrapMode: TextEdit.WordWrap
        }
    }
}
