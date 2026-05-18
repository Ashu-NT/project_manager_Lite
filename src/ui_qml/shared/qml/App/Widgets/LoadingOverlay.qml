import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property bool loading: false

    visible: root.loading
    color: Qt.rgba(Theme.AppTheme.surface.r, Theme.AppTheme.surface.g, Theme.AppTheme.surface.b, 0.75)

    BusyIndicator {
        anchors.centerIn: parent
        running: root.loading
    }
}
