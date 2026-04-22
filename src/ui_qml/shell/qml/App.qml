import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: app
    width: 1280
    height: 800
    visible: true
    title: shellContext.appTitle

    MainWindow {
        anchors.fill: parent
    }
}
