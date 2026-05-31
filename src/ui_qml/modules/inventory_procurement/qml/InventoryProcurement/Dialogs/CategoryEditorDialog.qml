import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Category"
    property var categoryTypeOptions: []
    property var categoryData: ({})
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
        categoryCodeField.text = String(state.categoryCode || "")
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
            "categoryCode": categoryCodeField.text,
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
        if (categoryCodeField.text.trim().length === 0) {
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

        AppControls.Label { text: "Category code"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: categoryCodeField; Layout.fillWidth: true; placeholderText: "SPARE" }

        AppControls.Label { text: "Name"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Spare Parts" }

        AppControls.Label { text: "Category type"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.ComboBox { id: categoryTypeCombo; Layout.fillWidth: true; model: root.formCategoryTypeOptions; textRole: "label" }

        AppControls.Label { text: "Description"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextArea { id: descriptionField; Layout.fillWidth: true; Layout.preferredHeight: 96; wrapMode: TextEdit.WordWrap; placeholderText: "Optional category description" }
    }

    AppControls.CheckBox { id: equipmentCheck; text: "Category represents equipment or reusable asset types" }
    AppControls.CheckBox { id: projectUsageCheck; text: "Available for project-management usage" }
    AppControls.CheckBox { id: maintenanceUsageCheck; text: "Available for maintenance usage" }
    AppControls.CheckBox { id: activeCheck; text: "Category is active" }
}
