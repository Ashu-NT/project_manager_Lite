pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.AnchoredPopup {
    id: root

    property var workspaceController: null
    property var state: null
    property var anchorItem: null

    anchorItem: root.anchorItem
    width: 280
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
            currentIndex: {
                const v = root.workspaceController
                    ? root.workspaceController.selectedActiveFilter : "all"
                return v === "active" ? 1 : v === "inactive" ? 2 : 0
            }
            onActivated: function(index) {
                const vals = ["all", "active", "inactive"]
                if (root.workspaceController !== null)
                    root.workspaceController.setActiveFilter(vals[index] || "all")
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
                ? root.state.categoryIndexForValue(
                    root.workspaceController ? root.workspaceController.selectedCategoryFilter : "all")
                : 0
            onActivated: function(index) {
                const opt = root.workspaceController
                    ? (root.workspaceController.categoryOptions || [])[index]
                    : null
                if (opt && root.workspaceController)
                    root.workspaceController.setCategoryFilter(String(opt.value || "all"))
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                Layout.fillWidth: true
                text: "Clear"
                iconName: "close"
                onClicked: {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setActiveFilter("all")
                        root.workspaceController.setCategoryFilter("all")
                    }
                    root.close()
                }
            }
            AppControls.SecondaryButton {
                Layout.fillWidth: true
                text: "Close"
                iconName: "close"
                onClicked: root.close()
            }
        }
    }
}
