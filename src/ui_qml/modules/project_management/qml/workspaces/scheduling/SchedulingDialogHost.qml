pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property string selectedProjectId: ""
    property var selectedActivityData: ({})
    property var dependencyTypeOptions: []
    property var dependencyTaskOptions: []
    property var dependencyTarget: ({})

    signal createBaselineRequested(var payload)
    signal createDependencyRequested(var payload)
    signal updateDependencyRequested(var payload)
    signal deleteDependencyRequested(string dependencyId)

    function _indexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) {
                return i
            }
        }
        return optionList.length > 0 ? 0 : -1
    }

    function openCreateBaselineDialog() {
        baselineNameField.text = ""
        createBaselineDialog.open()
    }

    function openCreateDependencyDialog(activityData) {
        root.dependencyTarget = activityData || ({})
        dependencyDirectionCombo.currentIndex = 0
        dependencyTaskCombo.currentIndex = root.dependencyTaskOptions.length > 0 ? 0 : -1
        dependencyTypeCombo.currentIndex = root._indexForValue(root.dependencyTypeOptions, "FS")
        dependencyLagField.text = "0"
        dependencyDialogTitle.text = "Create Dependency"
        dependencyPrimaryButton.text = "Create Dependency"
        dependencyEditorDialog.mode = "create"
        dependencyEditorDialog.open()
    }

    function openEditDependencyDialog(activityData, dependencyData) {
        root.dependencyTarget = dependencyData || ({})
        dependencyDialogTitle.text = "Edit Dependency"
        dependencyPrimaryButton.text = "Save Dependency"
        dependencyEditorDialog.mode = "edit"
        dependencyDirectionCombo.currentIndex = String((dependencyData.state || {}).directionLabel || "").toLowerCase().indexOf("predecessor") >= 0 ? 0 : 1
        dependencyTaskCombo.currentIndex = root._indexForValue(
            root.dependencyTaskOptions,
            String((dependencyData.state || {}).taskId || "")
        )
        dependencyTypeCombo.currentIndex = root._indexForValue(
            root.dependencyTypeOptions,
            String((dependencyData.state || {}).dependencyType || "FS")
        )
        dependencyLagField.text = String((dependencyData.state || {}).lagDays || 0)
        dependencyEditorDialog.open()
    }

    function openDeleteDependencyDialog(dependencyData) {
        root.dependencyTarget = dependencyData || ({})
        deleteDependencyDialog.open()
    }

    Dialog {
        id: createBaselineDialog
        modal: true
        width: 420
        padding: Theme.AppTheme.marginMd
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.divider
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingSm

            Label {
                text: "Save Baseline"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.sectionSize
                font.bold: true
            }

            Label {
                Layout.fillWidth: true
                text: "Create a controlled schedule snapshot for comparison and governance."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            TextField {
                id: baselineNameField
                Layout.fillWidth: true
                placeholderText: "Baseline name"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                Item { Layout.fillWidth: true }

                AppControls.SecondaryButton {
                    text: "Cancel"
                    iconName: "close"
                    onClicked: createBaselineDialog.close()
                }

                AppControls.PrimaryButton {
                    text: "Save Baseline"
                    iconName: "register"
                    enabled: String(root.selectedProjectId || "").length > 0
                    onClicked: {
                        root.createBaselineRequested({
                            "projectId": root.selectedProjectId,
                            "name": baselineNameField.text
                        })
                        createBaselineDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: dependencyEditorDialog
        property string mode: "create"
        modal: true
        width: 460
        padding: Theme.AppTheme.marginMd
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.divider
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingSm

            Label {
                id: dependencyDialogTitle
                text: "Create Dependency"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.sectionSize
                font.bold: true
            }

            Label {
                Layout.fillWidth: true
                text: dependencyEditorDialog.mode === "create"
                    ? "Connect the selected activity to a predecessor or successor."
                    : "Adjust dependency logic and lag for the selected activity relationship."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            ComboBox {
                id: dependencyTaskCombo
                Layout.fillWidth: true
                model: root.dependencyTaskOptions
                textRole: "label"
                enabled: dependencyEditorDialog.mode === "create"
            }

            ComboBox {
                id: dependencyDirectionCombo
                Layout.fillWidth: true
                model: [
                    { "label": "Predecessor", "value": "PREDECESSOR" },
                    { "label": "Successor", "value": "SUCCESSOR" }
                ]
                textRole: "label"
                enabled: dependencyEditorDialog.mode === "create"
            }

            ComboBox {
                id: dependencyTypeCombo
                Layout.fillWidth: true
                model: root.dependencyTypeOptions
                textRole: "label"
            }

            TextField {
                id: dependencyLagField
                Layout.fillWidth: true
                placeholderText: "Lag (days)"
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                Item { Layout.fillWidth: true }

                AppControls.SecondaryButton {
                    text: "Cancel"
                    iconName: "close"
                    onClicked: dependencyEditorDialog.close()
                }

                AppControls.PrimaryButton {
                    id: dependencyPrimaryButton
                    text: "Create Dependency"
                    iconName: "approve"
                    enabled: String(((root.selectedActivityData.state || {}).activityId || "")).length > 0
                    onClicked: {
                        const currentActivityId = String((root.selectedActivityData.state || {}).activityId || "")
                        const relatedTaskOption = root.dependencyTaskOptions[dependencyTaskCombo.currentIndex] || {}
                        const dependencyType = root.dependencyTypeOptions[dependencyTypeCombo.currentIndex] || {}
                        if (dependencyEditorDialog.mode === "create") {
                            root.createDependencyRequested({
                                "taskId": currentActivityId,
                                "relatedActivityId": String(relatedTaskOption.value || ""),
                                "relatedActivityName": String(relatedTaskOption.label || ""),
                                "relationshipDirection": String((dependencyDirectionCombo.model[dependencyDirectionCombo.currentIndex] || {}).value || "PREDECESSOR"),
                                "dependencyType": String(dependencyType.value || "FS"),
                                "lagDays": dependencyLagField.text
                            })
                        } else {
                            root.updateDependencyRequested({
                                "taskId": currentActivityId,
                                "dependencyId": String((root.dependencyTarget.state || {}).dependencyId || ""),
                                "relatedActivityName": String((root.dependencyTarget.state || {}).relatedActivityName || ""),
                                "dependencyType": String(dependencyType.value || "FS"),
                                "lagDays": dependencyLagField.text
                            })
                        }
                        dependencyEditorDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteDependencyDialog
        modal: true
        width: 420
        padding: Theme.AppTheme.marginMd
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.divider
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingSm

            Label {
                text: "Remove Dependency"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.sectionSize
                font.bold: true
            }

            Label {
                Layout.fillWidth: true
                text: String((root.dependencyTarget.state || {}).relatedActivityName || "")
                    ? "Remove the dependency link to " + String((root.dependencyTarget.state || {}).relatedActivityName || "") + "?"
                    : "Remove the selected dependency?"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                Item { Layout.fillWidth: true }

                AppControls.SecondaryButton {
                    text: "Cancel"
                    iconName: "close"
                    onClicked: deleteDependencyDialog.close()
                }

                AppControls.PrimaryButton {
                    text: "Remove"
                    iconName: "delete"
                    danger: true
                    onClicked: {
                        root.deleteDependencyRequested(String((root.dependencyTarget.state || {}).dependencyId || ""))
                        deleteDependencyDialog.close()
                    }
                }
            }
        }
    }
}
