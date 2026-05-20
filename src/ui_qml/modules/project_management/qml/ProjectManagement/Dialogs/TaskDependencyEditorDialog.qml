import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property var taskData: ({})
    property var taskOptions: []
    property var dependencyTypeOptions: []
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
    }

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
                text: root.taskData && root.taskData.title
                    ? "Define sequencing around " + root.taskData.title + "."
                    : "Define predecessor or successor flow for the selected task."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "Current task"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            Label {
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

                Label {
                    text: "Relationship"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                ComboBox {
                    id: relationshipCombo

                    Layout.fillWidth: true
                    model: root.relationshipOptions
                    textRole: "label"
                }

                Label {
                    text: "Linked task"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                ComboBox {
                    id: linkedTaskCombo

                    Layout.fillWidth: true
                    model: root.taskOptions
                    textRole: "label"
                }

                Label {
                    text: "Dependency type"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                ComboBox {
                    id: dependencyTypeCombo

                    Layout.fillWidth: true
                    model: root.dependencyTypeOptions
                    textRole: "label"
                }

                Label {
                    text: "Lag (days)"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: lagField

                    Layout.fillWidth: true
                    placeholderText: "0"
                }
            }

            Label {
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
            text: "Create Dependency"
            iconName: "add"
            enabled: (root.taskOptions || []).length > 0
            onClicked: root.submitted(root.buildPayload())
        }
    }
}
