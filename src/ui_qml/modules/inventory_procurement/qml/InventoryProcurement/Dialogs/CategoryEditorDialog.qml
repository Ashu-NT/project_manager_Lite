import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Category"
    property var categoryTypeOptions: []
    property var categoryData: ({})
    property string validationMessage: ""
    readonly property var formCategoryTypeOptions: categoryTypeOptions.filter(function(option) {
        return String(option.value || "") !== "all"
    })

    signal submitted(var payload)

    modal: true
    width: 560
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
        root.validationMessage = ""
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
            root.validationMessage = "Category code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "Category name is required."
            return
        }
        if (String((root.formCategoryTypeOptions[categoryTypeCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a category type before saving."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromCategory()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
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
                text: root.modeTitle === "Create Category"
                    ? "Define a reusable inventory category and its cross-module usage flags."
                    : "Update category governance, equipment scope, and usage flags."
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
                columns: root.width > 500 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label { text: "Category code" }
                TextField {
                    id: categoryCodeField
                    Layout.fillWidth: true
                    placeholderText: "SPARE"
                }

                Label { text: "Name" }
                TextField {
                    id: nameField
                    Layout.fillWidth: true
                    placeholderText: "Spare Parts"
                }

                Label { text: "Category type" }
                ComboBox {
                    id: categoryTypeCombo
                    Layout.fillWidth: true
                    model: root.formCategoryTypeOptions
                    textRole: "label"
                }

                Label { text: "Description" }
                TextArea {
                    id: descriptionField
                    Layout.fillWidth: true
                    Layout.preferredHeight: 96
                    wrapMode: TextEdit.WordWrap
                    placeholderText: "Optional category description"
                }
            }

            CheckBox {
                id: equipmentCheck
                text: "Category represents equipment or reusable asset types"
            }

            CheckBox {
                id: projectUsageCheck
                text: "Available for project-management usage"
            }

            CheckBox {
                id: maintenanceUsageCheck
                text: "Available for maintenance usage"
            }

            CheckBox {
                id: activeCheck
                text: "Category is active"
            }
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item {
            Layout.fillWidth: true
        }

        AppControls.SecondaryButton {
            objectName: "dialogCancelButton"
            text: "Cancel"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: "Save"
            onClicked: root.submitDialog()
        }
    }
}
