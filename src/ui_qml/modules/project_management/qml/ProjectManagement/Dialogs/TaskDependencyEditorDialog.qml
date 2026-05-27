import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property var taskData: ({})
    property var taskOptions: []
    property var dependencyTypeOptions: []
    property string validationMessage: ""
    readonly property var relationshipOptions: [
        {
            "value": "PREDECESSOR",
            "label": "Current task depends on other task"
        },
        {
            "value": "SUCCESSOR",
            "label": "Other task depends on current task"
        }
    ]

    signal submitted(var payload)

    modal: true
    width: 560
    title: "Create Dependency"
    closePolicy: Popup.CloseOnEscape
    padding: Theme.AppTheme.marginMd

    function indexForValue(options, targetValue) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function taskState() {
        return root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
    }

    function buildPayload() {
        const taskOption = root.taskOptions[linkedTaskCombo.currentIndex] || {}
        const relationshipOption = root.relationshipOptions[relationshipCombo.currentIndex] || {}
        const typeOption = root.dependencyTypeOptions[dependencyTypeCombo.currentIndex] || {}
        return {
            "taskId": String(root.taskState().taskId || ""),
            "linkedTaskId": String(taskOption.value || ""),
            "relationshipDirection": String(relationshipOption.value || "PREDECESSOR"),
            "dependencyType": String(typeOption.value || "FS"),
            "lagDays": lagField.text
        }
    }

    onOpened: {
        linkedTaskCombo.currentIndex = 0
        relationshipCombo.currentIndex = 0
        dependencyTypeCombo.currentIndex = root.indexForValue(root.dependencyTypeOptions, "FS")
        lagField.text = "0"
        root.validationMessage = ""
    }

    function submitDialog() {
        if (String((root.taskOptions[linkedTaskCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Select a linked task before creating the dependency."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surfaceRaised
        border.color: Theme.AppTheme.divider
        border.width: 1
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

            AppControls.Label {
                Layout.fillWidth: true
                text: root.taskData && root.taskData.title
                    ? "Define sequencing around " + root.taskData.title + "."
                    : "Define predecessor or successor flow for the selected task."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: root.validationMessage.length > 0
                text: root.validationMessage
                color: "#8B1E1E"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: "Current task"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: String(root.taskData.title || root.taskState().name || "Selected task")
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 520 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                AppControls.Label {
                    text: "Relationship"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                AppControls.ComboBox {
                    id: relationshipCombo

                    Layout.fillWidth: true
                    model: root.relationshipOptions
                    textRole: "label"
                }

                AppControls.Label {
                    text: "Linked task"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                AppControls.ComboBox {
                    id: linkedTaskCombo

                    Layout.fillWidth: true
                    model: root.taskOptions
                    textRole: "label"
                }

                AppControls.Label {
                    text: "Dependency type"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                AppControls.ComboBox {
                    id: dependencyTypeCombo

                    Layout.fillWidth: true
                    model: root.dependencyTypeOptions
                    textRole: "label"
                }

                AppControls.Label {
                    text: "Lag (days)"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                AppControls.TextField {
                    id: lagField

                    Layout.fillWidth: true
                    placeholderText: "0"
                }
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: (root.taskOptions || []).length === 0
                text: "At least one other task must exist in this project before you can create a dependency."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }
    }

    footer: AppControls.DialogActionFooter {

        Item {
            Layout.fillWidth: true
        }

        AppControls.SecondaryButton {
            objectName: "dialogCancelButton"
            text: "Cancel"
            iconName: "close"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: "Create Dependency"
            iconName: "add"
            enabled: (root.taskOptions || []).length > 0
            onClicked: root.submitDialog()
        }
    }
}

