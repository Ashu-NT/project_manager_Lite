import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property bool loading: false

    visible: root.loading
    color: Theme.AppTheme.overlayScrim

    BusyIndicator {
        anchors.centerIn: parent
        running: root.loading
    }
}
