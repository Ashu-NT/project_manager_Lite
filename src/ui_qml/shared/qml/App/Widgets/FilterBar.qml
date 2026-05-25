import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property string searchPlaceholder: "Search..."
    property string searchText: searchInput.text
    default property alias filterActions: filterSlot.data

    signal searchChanged(string text)
    signal refreshRequested()

    implicitHeight: Theme.AppTheme.toolbarHeight
    color: Theme.AppTheme.surfaceRaised
    radius: Theme.AppTheme.radiusMd

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingSm

        Rectangle {
            Layout.preferredWidth: 260
            implicitHeight: Theme.AppTheme.inputHeight
            radius: Theme.AppTheme.radiusSm
            color: Theme.AppTheme.surface
            border.color: searchInput.activeFocus
                ? Theme.AppTheme.focusBorder
                : Theme.AppTheme.subtleBorder
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.spacingSm
                anchors.rightMargin: Theme.AppTheme.spacingSm
                spacing: Theme.AppTheme.spacingXs

                AppIcons.AppIcon {
                    name: "search"
                    size: 12
                    iconColor: Theme.AppTheme.textMuted
                }

                TextField {
                    id: searchInput
                    Layout.fillWidth: true
                    placeholderText: root.searchPlaceholder
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    color: Theme.AppTheme.textPrimary
                    leftPadding: 0
                    rightPadding: 0
                    topPadding: 0
                    bottomPadding: 0
                    background: Item {}

                    Timer {
                        id: debounce
                        interval: 300
                        onTriggered: root.searchChanged(searchInput.text)
                    }

                    onTextChanged: debounce.restart()
                    Keys.onReturnPressed: {
                        debounce.stop()
                        root.searchChanged(searchInput.text)
                    }
                }
            }
        }

        Row {
            id: filterSlot
            spacing: Theme.AppTheme.spacingSm
        }

        Item {
            Layout.fillWidth: true
        }
    }
}

