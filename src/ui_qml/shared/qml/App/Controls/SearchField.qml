import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

Item {
    id: root

    property alias text: field.text
    property alias placeholderText: field.placeholderText
    property alias inputMethodHints: field.inputMethodHints
    property alias validator: field.validator
    property alias readOnly: field.readOnly
    property alias echoMode: field.echoMode
    property int debounceInterval: 280
    property bool showSearchIcon: true

    signal searchTriggered(string text)
    signal accepted()
    signal textEdited(string text)

    implicitWidth: 260
    implicitHeight: Theme.AppTheme.inputHeight

    function triggerSearch() {
        debounce.stop()
        root.searchTriggered(field.text)
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.AppTheme.radiusSm
        color: field.enabled
            ? Theme.AppTheme.surfaceRaised
            : Theme.AppTheme.surfaceOverlay
        border.width: 1
        border.color: field.activeFocus
            ? Theme.AppTheme.focusBorder
            : hoverHandler.hovered
                ? Theme.AppTheme.borderStrong
                : Theme.AppTheme.subtleBorder
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.spacingSm
        anchors.rightMargin: Theme.AppTheme.spacingSm
        spacing: Theme.AppTheme.spacingXs

        AppIcons.AppIcon {
            visible: root.showSearchIcon
            name: "search"
            size: Theme.AppTheme.toolbarIconSize
            iconColor: Theme.AppTheme.textMuted
        }

        TextField {
            id: field
            Layout.fillWidth: true
            enabled: root.enabled
            background: Item {}
            leftPadding: 0
            rightPadding: 0
            topPadding: 0
            bottomPadding: 0

            Timer {
                id: debounce
                interval: root.debounceInterval
                onTriggered: root.searchTriggered(field.text)
            }

            onTextEdited: root.textEdited(text)
            onTextChanged: debounce.restart()
            onAccepted: {
                root.accepted()
                root.triggerSearch()
            }
        }

        AppIcons.AppIcon {
            visible: field.text.length > 0
            name: "close"
            size: Theme.AppTheme.iconSm
            iconColor: clearHover.hovered
                ? Theme.AppTheme.textSecondary
                : Theme.AppTheme.textMuted

            HoverHandler {
                id: clearHover
                enabled: root.enabled && parent.visible
            }

            TapHandler {
                enabled: root.enabled && parent.visible
                onTapped: {
                    field.clear()
                    root.triggerSearch()
                }
            }
        }
    }

    HoverHandler {
        id: hoverHandler
    }
}
