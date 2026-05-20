import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property string searchPlaceholder: "Search..."
    property bool showRefresh: true
    property bool showExport: false
    property bool showCreate: false
    property bool showFilter: false
    property string createLabel: "New"
    property bool isBusy: false

    default property alias filterContent: filterSlot.data

    signal searchChanged(string text)
    signal filterClicked()
    signal refreshRequested()
    signal exportRequested()
    signal createRequested()

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
                    enabled: !root.isBusy
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
                        interval: 280
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

        Rectangle {
            visible: root.showFilter
            implicitWidth: filterRow.implicitWidth + 14
            implicitHeight: Theme.AppTheme.inputHeight - 4
            radius: Theme.AppTheme.radiusSm
            color: filterHover.containsMouse
                ? Theme.AppTheme.hoverSurface
                : Theme.AppTheme.surfaceOverlay

            Row {
                id: filterRow
                anchors.centerIn: parent
                spacing: Theme.AppTheme.spacingXs

                AppIcons.AppIcon {
                    name: "filter"
                    size: 11
                    iconColor: Theme.AppTheme.textMuted
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "Filters"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            MouseArea {
                id: filterHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.filterClicked()
            }
        }

        Item {
            Layout.fillWidth: true
        }

        AppControls.SecondaryButton {
            visible: root.showRefresh
            text: "Refresh"
            iconName: "refresh"
            enabled: !root.isBusy
            implicitWidth: 88
            onClicked: root.refreshRequested()
        }

        AppControls.SecondaryButton {
            visible: root.showExport
            text: "Export"
            iconName: "export"
            enabled: !root.isBusy
            implicitWidth: 88
            onClicked: root.exportRequested()
        }

        AppControls.PrimaryButton {
            visible: root.showCreate
            text: root.createLabel
            iconName: "add"
            enabled: !root.isBusy
            onClicked: root.createRequested()
        }
    }
}
