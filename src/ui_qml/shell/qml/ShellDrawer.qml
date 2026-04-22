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
            text: "Migrated QML workspaces register routes here."
            color: "#5d6a7e"
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: shellContext.navigationItems

            delegate: Rectangle {
                required property var modelData

                Layout.fillWidth: true
                height: 52
                radius: 14
                color: modelData.routeId === shellContext.currentRouteId ? "#dceaff" : "#ffffff"
                border.color: modelData.routeId === shellContext.currentRouteId ? "#8fb8ff" : "#d1ddec"

                Column {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    anchors.topMargin: 8
                    spacing: 2

                    Label {
                        text: modelData.title
                        color: "#1f4f93"
                        font.bold: true
                    }

                    Label {
                        text: modelData.moduleLabel + " / " + modelData.groupLabel
                        color: "#5d6a7e"
                        font.pixelSize: 11
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: shellContext.selectRoute(modelData.routeId)
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
