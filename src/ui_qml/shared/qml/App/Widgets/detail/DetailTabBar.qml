pragma ComponentBehavior: Bound
import QtQuick
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

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

        Flickable {
            anchors.fill: parent
            contentWidth: tabRow.implicitWidth
            contentHeight: height
            boundsBehavior: Flickable.StopAtBounds
            interactive: tabRow.implicitWidth > width
            clip: true

            Row {
                id: tabRow

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
                        readonly property bool hasCount: typeof tabItem.modelData !== "string"
                            && typeof tabItem.modelData.count === "number"
                            && tabItem.modelData.count >= 0

                        width: tabContent.implicitWidth + 24
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

                        Row {
                            id: tabContent
                            anchors.centerIn: parent
                            spacing: 6

                            AppControls.Label {
                                id: tabText
                                anchors.verticalCenter: parent.verticalCenter
                                text: tabItem.tabLabel
                                color: tabItem.isActive ? Theme.AppTheme.accent : Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: tabItem.isActive
                            }

                            Rectangle {
                                id: countBadge
                                anchors.verticalCenter: parent.verticalCenter
                                visible: tabItem.hasCount
                                width: Math.max(20, countText.implicitWidth + 10)
                                height: 20
                                radius: 10
                                color: tabItem.isActive
                                    ? Theme.AppTheme.accentSoft
                                    : Theme.AppTheme.surfaceAlt

                                AppControls.Label {
                                    id: countText
                                    anchors.centerIn: parent
                                    text: tabItem.hasCount ? String(tabItem.modelData.count) : ""
                                    color: tabItem.isActive
                                        ? Theme.AppTheme.accent
                                        : Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                            }
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
}
