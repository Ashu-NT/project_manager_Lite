import QtQuick
import QtQuick.Controls
import "../../shared/qml/theme" as Theme

ApplicationWindow {
    id: app
    width: 1280
    height: 800
    visible: true
    title: shellContext.appTitle
    color: Theme.AppTheme.appBackground

    MainWindow {
        anchors.fill: parent
    }
}
