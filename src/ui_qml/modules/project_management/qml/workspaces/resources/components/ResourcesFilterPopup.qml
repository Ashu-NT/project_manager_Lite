pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root
    objectName: "resourcesFilterPopup"

    property var workspaceController: null
    property var state: null

    // Draft selections, staged until Apply commits them to the controller.
    property string _draftActive: "all"
    property string _draftCategory: "all"

    title: "Filter Resources"
    width: 440
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    onAboutToShow: {
        root._draftActive = root.workspaceController ? root.workspaceController.selectedActiveFilter : "all"
        root._draftCategory = root.workspaceController ? root.workspaceController.selectedCategoryFilter : "all"
    }

    contentItem: ColumnLayout {
        objectName: "resourcesFilterContent"
        spacing: Theme.AppTheme.spacingMd

        Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                text: "Active Status"
                font.bold: true
                font.pixelSize: Theme.AppTheme.captionSize
                font.family: Theme.AppTheme.fontFamily
                color: Theme.AppTheme.textMuted
            }
            AppControls.ComboBox {
                Layout.fillWidth: true
                model: [
                    { "label": "All",      "value": "all"      },
                    { "label": "Active",   "value": "active"   },
                    { "label": "Inactive", "value": "inactive" }
                ]
                textRole: "label"
                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                currentIndex: root._draftActive === "active" ? 1 : root._draftActive === "inactive" ? 2 : 0
                onActivated: function(index) {
                    const vals = ["all", "active", "inactive"]
                    root._draftActive = vals[index] || "all"
                }
            }

            AppControls.Label {
                text: "Category"
                font.bold: true
                font.pixelSize: Theme.AppTheme.captionSize
                font.family: Theme.AppTheme.fontFamily
                color: Theme.AppTheme.textMuted
            }
            AppControls.ComboBox {
                Layout.fillWidth: true
                model: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                textRole: "label"
                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                currentIndex: root.state
                    ? root.state.categoryIndexForValue(root._draftCategory)
                    : 0
                onActivated: function(index) {
                    const opt = root.workspaceController
                        ? (root.workspaceController.categoryOptions || [])[index]
                        : null
                    root._draftCategory = String((opt && opt.value) || "all")
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        RowLayout {
            objectName: "resourcesFilterActions"
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            Layout.bottomMargin: Theme.AppTheme.spacingSm
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: "Clear"
                iconName: "refresh"
                onClicked: {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setActiveFilter("all")
                        root.workspaceController.setCategoryFilter("all")
                    }
                    root.close()
                }
            }
            Item { Layout.fillWidth: true }
            AppControls.SecondaryButton {
                text: "Close"
                iconName: "close"
                onClicked: root.close()
            }
            AppControls.PrimaryButton {
                text: "Apply"
                iconName: "approve"
                onClicked: {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setActiveFilter(root._draftActive)
                        root.workspaceController.setCategoryFilter(root._draftCategory)
                    }
                    root.close()
                }
            }
        }
    }
}
