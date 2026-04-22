import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: header
    height: 68
    radius: 20
    color: "#10233f"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 22
        anchors.rightMargin: 22

        Label {
            text: shellContext.appTitle
            color: "#f8fbff"
            font.pixelSize: 22
            font.bold: true
        }

        Item {
            Layout.fillWidth: true
        }

        Label {
            text: shellContext.userDisplayName || "QML migration shell"
            color: "#9fc1ff"
            font.pixelSize: 13
        }
    }
}
