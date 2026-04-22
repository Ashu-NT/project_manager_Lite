import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: drawer
    radius: 22
    color: "#eef4fb"
    border.color: "#d1ddec"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Label {
            text: "Navigation"
            color: "#253047"
            font.pixelSize: 20
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            text: "Migrated QML workspaces will register routes here."
            color: "#5d6a7e"
            wrapMode: Text.WordWrap
        }

        Rectangle {
            Layout.fillWidth: true
            height: 44
            radius: 12
            color: "#dceaff"

            Label {
                anchors.centerIn: parent
                text: "Shell / Runtime"
                color: "#1f4f93"
                font.bold: true
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
