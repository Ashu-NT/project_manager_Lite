pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var contextModel: ({
        "projectOptions": [],
        "teamOptions": [],
        "periodOptions": [],
        "unreadOptions": []
    })
    property string selectedProjectId: "all"
    property string selectedTeamId: "all"
    property string selectedPeriodKey: "all"
    property string selectedUnreadKey: "all"
    property bool isBusy: false
    property alias settingsButtonItem: settingsButton

    signal projectChanged(string projectId)
    signal teamChanged(string teamId)
    signal periodChanged(string periodKey)
    signal unreadChanged(string unreadKey)
    signal refreshRequested()
    signal settingsRequested()

    function _indexForValue(options, targetValue) {
        const list = options || []
        for (let i = 0; i < list.length; i += 1) {
            if (String(list[i].value || "") === String(targetValue || "")) {
                return i
            }
        }
        return 0
    }

    implicitHeight: Theme.AppTheme.toolbarHeight + Theme.AppTheme.spacingMd
    radius: Theme.AppTheme.radiusMd
    color: Theme.AppTheme.surfaceRaised
    border.color: Theme.AppTheme.subtleBorder
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingSm

        AppControls.ComboBox {
            Layout.preferredWidth: 180
            model: root.contextModel.projectOptions || []
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root._indexForValue(
                root.contextModel.projectOptions || [],
                root.selectedProjectId
            )
            onActivated: function(index) {
                const option = (root.contextModel.projectOptions || [])[index]
                if (option) {
                    root.projectChanged(String(option.value || "all"))
                }
            }
        }

        AppControls.ComboBox {
            Layout.preferredWidth: 150
            model: root.contextModel.teamOptions || []
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root._indexForValue(
                root.contextModel.teamOptions || [],
                root.selectedTeamId
            )
            onActivated: function(index) {
                const option = (root.contextModel.teamOptions || [])[index]
                if (option) {
                    root.teamChanged(String(option.value || "all"))
                }
            }
        }

        AppControls.ComboBox {
            Layout.preferredWidth: 148
            model: root.contextModel.periodOptions || []
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root._indexForValue(
                root.contextModel.periodOptions || [],
                root.selectedPeriodKey
            )
            onActivated: function(index) {
                const option = (root.contextModel.periodOptions || [])[index]
                if (option) {
                    root.periodChanged(String(option.value || "all"))
                }
            }
        }

        AppControls.ComboBox {
            Layout.preferredWidth: 150
            model: root.contextModel.unreadOptions || []
            textRole: "label"
            enabled: !root.isBusy
            currentIndex: root._indexForValue(
                root.contextModel.unreadOptions || [],
                root.selectedUnreadKey
            )
            onActivated: function(index) {
                const option = (root.contextModel.unreadOptions || [])[index]
                if (option) {
                    root.unreadChanged(String(option.value || "all"))
                }
            }
        }

        Item { Layout.fillWidth: true }

        AppControls.SecondaryButton {
            text: "Refresh"
            iconName: "refresh"
            enabled: !root.isBusy
            onClicked: root.refreshRequested()
        }

        AppControls.SecondaryButton {
            id: settingsButton
            text: "Settings"
            iconName: "settings"
            enabled: !root.isBusy
            onClicked: root.settingsRequested()
        }
    }
}
