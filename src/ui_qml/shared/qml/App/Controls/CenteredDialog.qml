import QtQuick
import QtQuick.Controls

Dialog {
    id: root

    property int minimumSideMargin: 24
    property int minimumTopMargin: 24

    parent: Overlay.overlay
    modal: true
    focus: true

    x: {
        const parentWidth = parent ? parent.width : width
        return Math.max(root.minimumSideMargin, Math.round((parentWidth - width) / 2))
    }
    y: {
        const parentHeight = parent ? parent.height : height
        return Math.max(root.minimumTopMargin, Math.round((parentHeight - height) / 2))
    }
}

