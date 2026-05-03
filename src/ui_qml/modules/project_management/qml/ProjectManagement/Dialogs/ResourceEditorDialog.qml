import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Resource"
    property var workerTypeOptions: []
    property var categoryOptions: []
    property var employeeOptions: []
    property var resourceData: ({})
    property string validationMessage: ""
    readonly property bool employeeWorkerSelected: String(root.currentWorkerTypeValue() || "") === "EMPLOYEE"

    signal submitted(var payload)

    modal: true
    width: 620
    height: Math.min(760, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 760)
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape

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
        root.validationMessage = ""
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
            root.validationMessage = "Select an employee before saving an employee-linked resource."
            return
        }
        if (!root.employeeWorkerSelected && nameField.text.trim().length === 0) {
            root.validationMessage = "Resource name is required."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromResource()

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
                text: root.modeTitle === "Create Resource"
                    ? "Set up a PM resource record for internal staffing or external support."
                    : "Update capacity, category, worker linkage, or resource availability."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                visible: root.validationMessage.length > 0
                text: root.validationMessage
                color: "#8B1E1E"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 560 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label {
                    text: "Worker type"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                ComboBox {
                    id: workerTypeCombo

                    Layout.fillWidth: true
                    model: root.workerTypeOptions
                    textRole: "label"
                    onCurrentIndexChanged: root.applyEmployeeDefaults()
                }

                Label {
                    text: "Employee"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                ComboBox {
                    id: employeeCombo

                    Layout.fillWidth: true
                    model: root.employeeOptions
                    textRole: "label"
                    enabled: root.employeeWorkerSelected
                    onCurrentIndexChanged: root.applyEmployeeDefaults()
                }

                Label {
                    text: "Shared context"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                Label {
                    id: employeeContextValue

                    Layout.fillWidth: true
                    text: "-"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Label {
                    text: "Resource name"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: nameField

                    Layout.fillWidth: true
                    placeholderText: "Electrical Crew"
                    readOnly: root.employeeWorkerSelected
                }

                Label {
                    text: "Role"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: roleField

                    Layout.fillWidth: true
                    placeholderText: "Lead Technician"
                    readOnly: root.employeeWorkerSelected
                }

                Label {
                    text: "Category"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                ComboBox {
                    id: categoryCombo

                    Layout.fillWidth: true
                    model: root.categoryOptions
                    textRole: "label"
                }

                Label {
                    text: "Hourly rate"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: hourlyRateField

                    Layout.fillWidth: true
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    placeholderText: "95.00"
                }

                Label {
                    text: "Capacity (%)"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: capacityField

                    Layout.fillWidth: true
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    placeholderText: "100.0"
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
                    text: "Address"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: addressField

                    Layout.fillWidth: true
                    placeholderText: "Site office or vendor address"
                }

                Label {
                    text: "Contact"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: contactField

                    Layout.fillWidth: true
                    placeholderText: "name@example.com"
                    readOnly: root.employeeWorkerSelected
                }
            }

            CheckBox {
                id: activeCheck

                text: "Resource is active and available for planning"
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
            text: root.modeTitle === "Create Resource" ? "Create Resource" : "Save Changes"
            onClicked: root.submitDialog()
        }
    }
}
