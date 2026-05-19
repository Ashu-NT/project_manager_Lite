pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var tabs: []
    property int currentIndex: 0

    signal tabSelected(int index)

    implicitHeight: 36

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.surface

        // Bottom border
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: Theme.AppTheme.border
        }

        Row {
            anchors.fill: parent

            Repeater {
                model: root.tabs

                delegate: Item {
                    id: tabItem
                    required property var modelData
                    required property int index

                    readonly property bool isActive: root.currentIndex === tabItem.index
                    readonly property string tabLabel: typeof tabItem.modelData === "string"
                        ? tabItem.modelData
                        : (tabItem.modelData.label || "")

                    width: tabText.implicitWidth + 24
                    height: 36

                    // Hover background
                    Rectangle {
                        anchors.fill: parent
                        color: tabHover.containsMouse && !tabItem.isActive
                            ? Theme.AppTheme.hoverSurface
                            : "transparent"
                    }

                    // Active bottom accent
                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 2
                        color: Theme.AppTheme.accent
                        visible: tabItem.isActive
                    }

                    Label {
                        id: tabText
                        anchors.centerIn: parent
                        text: tabItem.tabLabel
                        color: tabItem.isActive ? Theme.AppTheme.accent : Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: tabItem.isActive
                    }

                    MouseArea {
                        id: tabHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.tabSelected(tabItem.index)
                    }
                }
            }
        }
    }
}
