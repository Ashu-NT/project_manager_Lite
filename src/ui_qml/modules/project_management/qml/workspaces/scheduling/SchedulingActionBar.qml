pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var actions: []
    property bool isBusy: false
    default property alias content: leadingLayout.data

    signal actionTriggered(string actionId)

    implicitHeight: Math.max(
        Theme.AppTheme.inputHeight + (Theme.AppTheme.spacingSm * 2),
        actionLayout.implicitHeight + (Theme.AppTheme.spacingSm * 2)
    )
    radius: Theme.AppTheme.radiusSm
    color: Theme.AppTheme.surfaceAlt
    border.color: Theme.AppTheme.subtleBorder
    border.width: 1

    RowLayout {
        id: actionLayout
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingSm

        RowLayout {
            id: leadingLayout
            spacing: Theme.AppTheme.spacingSm
        }

        Item {
            Layout.fillWidth: true
        }

        Repeater {
            model: root.actions

            delegate: AppControls.SecondaryButton {
                required property var modelData

                text: String(modelData.label || "")
                iconName: String(modelData.icon || "")
                danger: Boolean(modelData.danger || false)
                enabled: !root.isBusy && (modelData.enabled !== false)
                onClicked: root.actionTriggered(String(modelData.id || ""))
            }
        }
    }
}
