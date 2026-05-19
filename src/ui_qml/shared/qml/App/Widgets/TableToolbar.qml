import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// Toolbar for enterprise tables: search | filters | refresh | export | create
Rectangle {
    id: root

    property string searchPlaceholder: "Search..."
    property bool showRefresh: true
    property bool showExport: false
    property bool showCreate: false
    property string createLabel: "New"
    property bool isBusy: false

    default property alias filterContent: filterSlot.data

    signal searchChanged(string text)
    signal refreshRequested()
    signal exportRequested()
    signal createRequested()

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

        // Search
        TextField {
            id: searchField
            Layout.preferredWidth: 220
            placeholderText: root.searchPlaceholder
            enabled: !root.isBusy
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
                interval: 280
                onTriggered: root.searchChanged(searchField.text)
            }

            onTextChanged: debounce.restart()
            Keys.onReturnPressed: {
                debounce.stop()
                root.searchChanged(searchField.text)
            }
        }

        // Custom filter slot
        Row {
            id: filterSlot
            spacing: Theme.AppTheme.spacingSm
        }

        Item { Layout.fillWidth: true }

        // Refresh
        AppControls.SecondaryButton {
            visible: root.showRefresh
            text: "Refresh"
            enabled: !root.isBusy
            implicitWidth: 80
            onClicked: root.refreshRequested()
        }

        // Export
        AppControls.SecondaryButton {
            visible: root.showExport
            text: "Export"
            enabled: !root.isBusy
            implicitWidth: 80
            onClicked: root.exportRequested()
        }

        // Create / New
        AppControls.PrimaryButton {
            visible: root.showCreate
            text: root.createLabel
            enabled: !root.isBusy
            onClicked: root.createRequested()
        }
    }
}
