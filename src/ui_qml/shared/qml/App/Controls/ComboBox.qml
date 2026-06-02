pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls as QQC2
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

QQC2.ComboBox {
    id: control

    property string placeholderText: ""

    implicitHeight: Theme.AppTheme.inputHeight
    implicitWidth: Math.max(160, contentItem.implicitWidth + Theme.AppTheme.spacingXl)
    leftPadding: Theme.AppTheme.spacingSm + 2
    rightPadding: Theme.AppTheme.spacingXl + Theme.AppTheme.spacingSm
    topPadding: 0
    bottomPadding: 0
    font.family: Theme.AppTheme.fontFamily
    font.pixelSize: Theme.AppTheme.bodySize

    contentItem: Text {
        leftPadding: 0
        rightPadding: 0
        verticalAlignment: Text.AlignVCenter
        text: control.currentIndex >= 0
            ? control.displayText
            : control.placeholderText
        color: control.currentIndex >= 0
            ? (control.enabled ? Theme.AppTheme.textPrimary : Theme.AppTheme.textMuted)
            : Theme.AppTheme.textMuted
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.bodySize
        elide: Text.ElideRight
    }

    indicator: AppIcons.AppIcon {
        anchors.right: parent.right
        anchors.rightMargin: Theme.AppTheme.spacingSm
        anchors.verticalCenter: parent.verticalCenter
        name: "chevron_down"
        size: Theme.AppTheme.toolbarIconSize
        iconColor: Theme.AppTheme.textMuted
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusSm
        color: control.enabled
            ? Theme.AppTheme.surfaceRaised
            : Theme.AppTheme.surfaceOverlay
        border.width: 1
        border.color: control.activeFocus
            ? Theme.AppTheme.focusBorder
            : control.hovered
                ? Theme.AppTheme.borderStrong
                : Theme.AppTheme.subtleBorder
    }

    delegate: QQC2.ItemDelegate {
        required property int index

        width: control.width
        highlighted: control.highlightedIndex === index
        padding: 0

        contentItem: Text {
            leftPadding: Theme.AppTheme.spacingSm + 2
            rightPadding: Theme.AppTheme.spacingSm + 2
            verticalAlignment: Text.AlignVCenter
            text: control.textAt(index)
            color: highlighted
                ? Theme.AppTheme.accent
                : Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            elide: Text.ElideRight
        }

        background: Rectangle {
            color: parent.highlighted
                ? Theme.AppTheme.selectedSurface
                : hovered
                    ? Theme.AppTheme.hoverSurface
                    : "transparent"
        }
    }

    popup: QQC2.Popup {
        y: control.height + Theme.AppTheme.spacingXs
        width: control.width
        padding: Theme.AppTheme.spacingXs

        background: Rectangle {
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.dialogBorder
            border.width: 1
        }

        contentItem: ListView {
            clip: true
            implicitHeight: Math.min(contentHeight, 280)
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            boundsBehavior: Flickable.StopAtBounds
            QQC2.ScrollBar.vertical: QQC2.ScrollBar { }
        }
    }
}
