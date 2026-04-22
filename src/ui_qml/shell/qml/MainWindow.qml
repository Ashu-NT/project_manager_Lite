import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        ShellHeader {
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            ShellDrawer {
                Layout.preferredWidth: 280
                Layout.fillHeight: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 22
                color: "#ffffff"
                border.color: "#dbe3ef"

                Label {
                    anchors.centerIn: parent
                    text: "QML shell ready for migrated workspaces"
                    color: "#253047"
                    font.pixelSize: 22
                    font.bold: true
                }
            }
        }
    }
}
