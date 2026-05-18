import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property string searchPlaceholder: "Search..."
    property string searchText: searchField.text
    default property alias filterActions: filterSlot.data

    signal searchChanged(string text)
    signal refreshRequested()

    implicitHeight: Theme.AppTheme.toolbarHeight
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.subtleBorder
    border.width: 1
    radius: Theme.AppTheme.radiusSm

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.spacingMd
        anchors.rightMargin: Theme.AppTheme.spacingMd
        spacing: Theme.AppTheme.spacingSm

        TextField {
            id: searchField
            Layout.preferredWidth: 220
            placeholderText: root.searchPlaceholder
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            leftPadding: Theme.AppTheme.spacingSm
            rightPadding: Theme.AppTheme.spacingSm
            background: Rectangle {
                radius: Theme.AppTheme.radiusSm
                color: Theme.AppTheme.surfaceSunken
                border.color: searchField.activeFocus
                    ? Theme.AppTheme.focusBorder
                    : Theme.AppTheme.border
                border.width: searchField.activeFocus ? 1.5 : 1
            }

            Timer {
                id: debounce
                interval: 300
                onTriggered: root.searchChanged(searchField.text)
            }

            onTextChanged: debounce.restart()
            Keys.onReturnPressed: {
                debounce.stop()
                root.searchChanged(searchField.text)
            }
        }

        Row {
            id: filterSlot
            spacing: Theme.AppTheme.spacingSm
        }

        Item { Layout.fillWidth: true }
    }
}
