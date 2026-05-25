pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// Floating multi-select action bar.
// Position with anchors.horizontalCenter + anchors.bottom in the parent Item.
// actions: [{id, label, icon, danger, enabled}]
Rectangle {
    id: root

    property int selectedCount: 0
    property bool busy:         false
    property var  actions:      []

    signal cancelRequested()
    signal actionTriggered(string id)

    function actionButtonForId(actionId) {
        const wantedId = String(actionId || "")
        for (let i = 0; i < actionRepeater.count; i += 1) {
            const item = actionRepeater.itemAt(i)
            if (item && String(item.objectName || "") === wantedId) {
                return item
            }
        }
        return null
    }

    visible: root.selectedCount > 0
    height:  40
    radius:  Theme.AppTheme.radiusMd
    color:   Theme.AppTheme.surfaceRaised
    width:   _row.implicitWidth + Theme.AppTheme.marginMd * 2

    RowLayout {
        id: _row
        anchors.centerIn: parent
        spacing: Theme.AppTheme.spacingSm

        Label {
            text:           root.selectedCount + " selected"
            color:          Theme.AppTheme.textPrimary
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold:      true
        }

        Rectangle {
            implicitWidth: 1
            implicitHeight: 20
            color: Theme.AppTheme.divider
        }

        AppControls.SecondaryButton {
            text:         "Cancel"
            iconName:     "close"
            implicitWidth: 80
            onClicked:    root.cancelRequested()
        }

        Repeater {
            id: actionRepeater
            model: root.actions
            delegate: AppControls.SecondaryButton {
                id: actionButton
                required property var modelData
                readonly property string _actionId: String(modelData.id || "")
                objectName: _actionId
                text:      modelData.label  || ""
                iconName:  modelData.icon   || ""
                danger:    modelData.danger || false
                enabled:   !root.busy && (modelData.enabled !== false)
                implicitWidth: 80
                onClicked: root.actionTriggered(String(modelData.id || ""))
            }
        }
    }
}
