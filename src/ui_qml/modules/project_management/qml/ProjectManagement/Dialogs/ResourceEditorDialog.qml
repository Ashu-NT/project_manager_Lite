import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Resource"
    property var workerTypeOptions: []
    property var categoryOptions: []
    property var employeeOptions: []
    property var resourceData: ({})
    readonly property bool employeeWorkerSelected: String(root.currentWorkerTypeValue() || "") === "EMPLOYEE"

    signal submitted(var payload)

    title:        root.modeTitle
    subtitle:     root.modeTitle === "Create Resource"
        ? "Set up a PM resource record for internal staffing or external support."
        : "Update capacity, category, worker linkage, or resource availability."
    primaryText:  root.modeTitle === "Create Resource" ? "Create Resource" : "Save Changes"
    primaryIcon:  root.modeTitle === "Create Resource" ? "add" : "save"
    width: 620

    onOpened:   root.populateFromResource()
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

    function currentWorkerTypeValue() {
        var option = root.workerTypeOptions[workerTypeCombo.currentIndex]
        return String(option ? option.value || "EXTERNAL" : "EXTERNAL")
    }

    function selectedEmployeeOption() {
        var option = root.employeeOptions[employeeCombo.currentIndex]
        return option || ({})
    }

    function applyEmployeeDefaults() {
        var option = root.selectedEmployeeOption()
        if (!root.employeeWorkerSelected) {
            employeeContextValue.text = "-"
            return
        }
        employeeContextValue.text = String(option.context || "Select an employee to inherit shared context.")
        if (String(option.value || "").length > 0) {
            nameField.text = String(option.name || "")
            roleField.text = String(option.title || "")
            contactField.text = String(option.contact || "")
        }
    }

    function populateFromResource() {
        var state = root.resourceData && root.resourceData.state ? root.resourceData.state : (root.resourceData || {})
        workerTypeCombo.currentIndex = root.indexForValue(root.workerTypeOptions, state.workerType || "EXTERNAL")
        employeeCombo.currentIndex = root.indexForValue(root.employeeOptions, state.employeeId || "")
        categoryCombo.currentIndex = root.indexForValue(root.categoryOptions, state.costType || "LABOR")
        nameField.text = String(state.name || "")
        roleField.text = String(state.role || "")
        hourlyRateField.text = String(state.hourlyRate || "0.00")
        capacityField.text = String(state.capacityPercent || "100.0")
        currencyField.text = String(state.currency || "")
        addressField.text = String(state.address || "")
        contactField.text = String(state.contact || "")
        activeCheck.checked = state.isActive !== false
        root.errorMessage = ""
        root.applyEmployeeDefaults()
    }

    function buildPayload() {
        return {
            "name": nameField.text,
            "role": roleField.text,
            "hourlyRate": hourlyRateField.text,
            "capacityPercent": capacityField.text,
            "currency": currencyField.text,
            "costType": String((root.categoryOptions[categoryCombo.currentIndex] || { "value": "LABOR" }).value || "LABOR"),
            "address": addressField.text,
            "contact": contactField.text,
            "workerType": root.currentWorkerTypeValue(),
            "employeeId": String((root.employeeOptions[employeeCombo.currentIndex] || { "value": "" }).value || ""),
            "isActive": activeCheck.checked
        }
    }

    function submitDialog() {
        if (root.employeeWorkerSelected && String((root.employeeOptions[employeeCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Select an employee before saving an employee-linked resource."
            return
        }
        if (!root.employeeWorkerSelected && nameField.text.trim().length === 0) {
            root.errorMessage = "Resource name is required."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 560 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Worker type"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.ComboBox { id: workerTypeCombo; Layout.fillWidth: true; model: root.workerTypeOptions; textRole: "label"; onCurrentIndexChanged: root.applyEmployeeDefaults() }

        AppControls.Label { text: "Employee"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.ComboBox { id: employeeCombo; Layout.fillWidth: true; model: root.employeeOptions; textRole: "label"; enabled: root.employeeWorkerSelected; onCurrentIndexChanged: root.applyEmployeeDefaults() }

        AppControls.Label { text: "Shared context"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.Label { id: employeeContextValue; Layout.fillWidth: true; text: "-"; color: Theme.AppTheme.textSecondary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; wrapMode: Text.WordWrap }

        AppControls.Label { text: "Resource name"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Electrical Crew"; readOnly: root.employeeWorkerSelected }

        AppControls.Label { text: "Role"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: roleField; Layout.fillWidth: true; placeholderText: "Lead Technician"; readOnly: root.employeeWorkerSelected }

        AppControls.Label { text: "Category"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.ComboBox { id: categoryCombo; Layout.fillWidth: true; model: root.categoryOptions; textRole: "label" }

        AppControls.Label { text: "Hourly rate"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: hourlyRateField; Layout.fillWidth: true; inputMethodHints: Qt.ImhFormattedNumbersOnly; placeholderText: "95.00" }

        AppControls.Label { text: "Capacity (%)"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: capacityField; Layout.fillWidth: true; inputMethodHints: Qt.ImhFormattedNumbersOnly; placeholderText: "100.0" }

        AppControls.Label { text: "Currency"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: currencyField; Layout.fillWidth: true; placeholderText: "EUR" }

        AppControls.Label { text: "Address"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: addressField; Layout.fillWidth: true; placeholderText: "Site office or vendor address" }

        AppControls.Label { text: "Contact"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
        AppControls.TextField { id: contactField; Layout.fillWidth: true; placeholderText: "name@example.com"; readOnly: root.employeeWorkerSelected }
    }

    AppControls.CheckBox {
        id: activeCheck
        text: "Resource is active and available for planning"
    }
}
