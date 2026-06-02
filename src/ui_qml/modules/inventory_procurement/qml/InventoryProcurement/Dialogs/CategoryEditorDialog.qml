import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Category"
    property var categoryTypeOptions: []
    property var categoryData: ({})
    property var workspaceController: null
    property string categoryCode: ""
    readonly property var formCategoryTypeOptions: categoryTypeOptions.filter(function(option) {
        return String(option.value || "") !== "all"
    })

    signal submitted(var payload)

    title:        root.modeTitle
    subtitle:     root.modeTitle === "Create Category"
        ? "Define a reusable inventory category and its cross-module usage flags."
        : "Update category governance, equipment scope, and usage flags."
    primaryText:  "Save"
    primaryIcon:  "save"
    width: 560

    onOpened:   root.populateFromCategory()
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromCategory() {
        var state = root.categoryData && root.categoryData.state ? root.categoryData.state : (root.categoryData || {})
        root.categoryCode = String(state.categoryCode || "")
        nameField.text = String(state.name || "")
        descriptionField.text = String(state.description || "")
        categoryTypeCombo.currentIndex = root.indexForValue(root.formCategoryTypeOptions, state.categoryType || "")
        equipmentCheck.checked = state.isEquipment === true
        projectUsageCheck.checked = state.supportsProjectUsage === true
        maintenanceUsageCheck.checked = state.supportsMaintenanceUsage === true
        activeCheck.checked = state.isActive !== false
        root.errorMessage = ""
    }

    function buildPayload() {
        var selectedType = root.formCategoryTypeOptions[categoryTypeCombo.currentIndex] || { "value": "" }
        return {
            "categoryCode": root.categoryCode,
            "name": nameField.text,
            "description": descriptionField.text,
            "categoryType": String(selectedType.value || ""),
            "isEquipment": equipmentCheck.checked,
            "supportsProjectUsage": projectUsageCheck.checked,
            "supportsMaintenanceUsage": maintenanceUsageCheck.checked,
            "isActive": activeCheck.checked
        }
    }

    function submitDialog() {
        if (root.categoryCode.trim().length === 0) {
            root.errorMessage = "Category code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Category name is required."
            return
        }
        if (String((root.formCategoryTypeOptions[categoryTypeCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a category type before saving."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 500 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.CodeFieldRow {
            Layout.columnSpan: 2
            Layout.fillWidth: true
            label: "Category code"
            value: root.categoryCode
            placeholderText: "Auto-generated if empty"
            required: true
            generateVisible: true
            busy: root.busy
            onValueEdited: function(code) { root.categoryCode = code }
            onGenerateRequested: {
                if (root.workspaceController) {
                    const suggested = root.workspaceController.generateEntityCode("category", root.buildPayload())
                    if (suggested && suggested.length > 0) {
                        root.categoryCode = suggested
                    }
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Name"
            required: true
            AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Spare Parts" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Category type"
            required: true
            AppControls.ComboBox { id: categoryTypeCombo; Layout.fillWidth: true; model: root.formCategoryTypeOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Description"
            AppControls.TextArea { id: descriptionField; Layout.fillWidth: true; Layout.preferredHeight: 96; wrapMode: TextEdit.WordWrap; placeholderText: "Optional category description" }
        }
    }

    AppControls.CheckBox { id: equipmentCheck; text: "Category represents equipment or reusable asset types" }
    AppControls.CheckBox { id: projectUsageCheck; text: "Available for project-management usage" }
    AppControls.CheckBox { id: maintenanceUsageCheck; text: "Available for maintenance usage" }
    AppControls.CheckBox { id: activeCheck; text: "Category is active" }
}
