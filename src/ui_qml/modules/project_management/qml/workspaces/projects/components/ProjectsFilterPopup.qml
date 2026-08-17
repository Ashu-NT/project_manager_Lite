pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property var workspaceController: null
    property var state: null

    title: "Filter Projects"
    width: 320
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                text: "Status"
                font.bold: true
                font.pixelSize: Theme.AppTheme.captionSize
                font.family: Theme.AppTheme.fontFamily
                color: Theme.AppTheme.textMuted
            }

            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                textRole: "label"
                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                currentIndex: root.state
                    ? root.state.statusIndexForValue(
                        root.workspaceController ? root.workspaceController.selectedStatusFilter : "all")
                    : 0
                onActivated: function(index) {
                    const opt = root.workspaceController
                        ? (root.workspaceController.statusOptions || [])[index]
                        : null
                    if (opt && root.workspaceController)
                        root.workspaceController.setStatusFilter(String(opt.value || "all"))
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            Layout.bottomMargin: Theme.AppTheme.spacingSm
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: "Clear"
                iconName: "refresh"
                onClicked: {
                    if (root.workspaceController !== null)
                        root.workspaceController.setStatusFilter("all")
                    root.close()
                }
            }
            Item { Layout.fillWidth: true }
            AppControls.SecondaryButton {
                text: "Close"
                iconName: "close"
                onClicked: root.close()
            }
        }
    }
}
