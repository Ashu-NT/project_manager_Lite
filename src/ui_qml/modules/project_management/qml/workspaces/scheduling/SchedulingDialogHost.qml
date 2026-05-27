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

    signal createBaselineRequested(var payload)

    function openCreateBaselineDialog() {
        baselineNameField.text = ""
        createBaselineDialog.open()
    }

    AppControls.CenteredDialog {
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

            AppControls.Label {
                text: "Save Baseline"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.sectionSize
                font.bold: true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: "Create a controlled schedule snapshot for comparison and governance."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            AppControls.TextField {
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

}

