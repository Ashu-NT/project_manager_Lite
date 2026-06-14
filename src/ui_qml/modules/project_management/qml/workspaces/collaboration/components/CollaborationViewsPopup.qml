pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.AnchoredPopup {
    id: root

    signal viewSelected(string panelId, string unreadKey)

    width: 240
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: Theme.AppTheme.dialogPadding

    background: Rectangle {
        radius: Theme.AppTheme.radiusMd
        color: Theme.AppTheme.dialogBackground
        border.color: Theme.AppTheme.dialogBorder
        border.width: 1
    }

    ColumnLayout {
        width: parent.width
        spacing: Theme.AppTheme.spacingSm

        Repeater {
            model: [
                { "label": "Operational Inbox", "panelId": "inbox",       "unread": "all" },
                { "label": "Mentions Focus",     "panelId": "mentions",    "unread": "unread" },
                { "label": "Pending Approvals",  "panelId": "approvals",   "unread": "attention" },
                { "label": "Activity Journal",   "panelId": "activity",    "unread": "all" },
                { "label": "Team Updates",        "panelId": "team_updates","unread": "all" }
            ]

            delegate: AppControls.SecondaryButton {
                required property var modelData
                Layout.fillWidth: true
                text: String(modelData.label || "")
                onClicked: {
                    root.viewSelected(String(modelData.panelId || "inbox"), String(modelData.unread || "all"))
                    root.close()
                }
            }
        }
    }
}
