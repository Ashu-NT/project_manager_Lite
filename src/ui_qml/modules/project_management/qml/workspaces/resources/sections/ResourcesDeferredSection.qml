pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property string title: ""
    property string message: ""

    implicitHeight: card.implicitHeight

    AppWidgets.SectionCard {
        id: card
        anchors.left: parent.left
        anchors.right: parent.right
        title: root.title
        outlined: true
        implicitHeight: content.implicitHeight + Theme.AppTheme.marginMd * 2

        ColumnLayout {
            id: content
            anchors.fill: parent
            anchors.margins: Theme.AppTheme.marginMd
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                Layout.fillWidth: true
                text: root.message
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }
    }
}
