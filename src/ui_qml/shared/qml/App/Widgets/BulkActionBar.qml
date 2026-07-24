pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property bool active: true
    property int selectedCount: 0
    property bool busy: false
    property var actions: []

    readonly property real _naturalWidth: _contentRow.implicitWidth + Theme.AppTheme.marginMd * 2
    readonly property real _maxWidth: parent ? parent.width : _naturalWidth
    readonly property real _resolvedWidth: Math.min(_maxWidth, _naturalWidth)

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

    visible: root.active && root.selectedCount > 0
    width: _resolvedWidth
    implicitWidth: _resolvedWidth
    implicitHeight: _contentRow.implicitHeight + Theme.AppTheme.spacingSm * 2
    height: implicitHeight
    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surfaceRaised
    border.color: Theme.AppTheme.borderStrong
    border.width: 1
    clip: true

    RowLayout {
        id: _contentRow
        anchors.left: parent.left
        anchors.leftMargin: Theme.AppTheme.marginMd
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.AppTheme.spacingSm

        Rectangle {
            implicitWidth: _selectionLabel.implicitWidth + Theme.AppTheme.marginMd
            implicitHeight: Theme.AppTheme.toolbarHeight
            radius: Theme.AppTheme.radiusSm
            color: Theme.AppTheme.accentSoft
            border.color: Theme.AppTheme.divider
            border.width: 1

            AppControls.Label {
                id: _selectionLabel
                anchors.centerIn: parent
                text: root.selectedCount + " selected"
                color: Theme.AppTheme.accent
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }
        }

        AppControls.SecondaryButton {
            text: "Clear"
            iconName: "close"
            enabled: !root.busy
            onClicked: root.cancelRequested()
        }

        Repeater {
            id: actionRepeater
            model: root.actions
            delegate: AppControls.SecondaryButton {
                required property var modelData
                readonly property string _actionId: String(modelData.id || "")
                objectName: _actionId
                text: modelData.label || ""
                iconName: modelData.icon || ""
                danger: modelData.danger || false
                enabled: !root.busy && (modelData.enabled !== false)
                onClicked: root.actionTriggered(String(modelData.id || ""))
            }
        }
    }
}
