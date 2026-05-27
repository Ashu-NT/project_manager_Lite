import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

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

        AppControls.SearchField {
            id: searchInput
            Layout.preferredWidth: 260
            placeholderText: root.searchPlaceholder
            debounceInterval: 300
            onSearchTriggered: function(text) {
                root.searchChanged(text)
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

