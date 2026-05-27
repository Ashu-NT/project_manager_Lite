import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property int minimumSideMargin: Theme.AppTheme.dialogPadding
    property int minimumTopMargin: Theme.AppTheme.dialogPadding

    parent: Overlay.overlay
    modal: true
    focus: true
    implicitWidth: Math.min(Theme.AppTheme.dialogFormWidth, Theme.AppTheme.dialogMaxWidth)

    Overlay.modal: Rectangle {
        color: Theme.AppTheme.overlayScrim
    }

    background: Item {
        Rectangle {
            anchors.fill: parent
            anchors.margins: -6
            radius: Theme.AppTheme.radiusLg + 4
            color: Theme.AppTheme.shadowColor
            opacity: 0.55
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: -2
            radius: Theme.AppTheme.radiusLg + 2
            color: Theme.AppTheme.dialogShadow
            opacity: 0.18
        }

        Rectangle {
            anchors.fill: parent
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.dialogBackground
            border.color: Theme.AppTheme.dialogBorder
            border.width: 1
        }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: Math.min(Theme.AppTheme.dialogHeaderHeight, parent.height)
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.dialogHeaderBackground
            opacity: 0.45
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: Math.min(Theme.AppTheme.dialogFooterHeight, parent.height)
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.dialogFooterBackground
            opacity: 0.3
        }
    }

    x: {
        const parentWidth = parent ? parent.width : width
        return Math.max(root.minimumSideMargin, Math.round((parentWidth - width) / 2))
    }
    y: {
        const parentHeight = parent ? parent.height : height
        return Math.max(root.minimumTopMargin, Math.round((parentHeight - height) / 2))
    }
}

