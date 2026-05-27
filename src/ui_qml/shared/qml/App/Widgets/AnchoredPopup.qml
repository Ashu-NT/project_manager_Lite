pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme

Popup {
    id: root

    property Item anchorItem: null
    property string placement: "below-right"
    property real anchorMargin: Theme.AppTheme.spacingXs
    property int minimumMargin: Theme.AppTheme.marginSm
    property bool clampToParent: true

    parent: Overlay.overlay

    function reposition() {
        if (!root.anchorItem || !root.parent) {
            return
        }

        const anchorLeft = root.anchorItem.mapToItem(root.parent, 0, 0)
        const anchorRight = root.anchorItem.mapToItem(root.parent, root.anchorItem.width, 0)
        const anchorBottomLeft = root.anchorItem.mapToItem(root.parent, 0, root.anchorItem.height)
        const anchorBottomRight = root.anchorItem.mapToItem(root.parent, root.anchorItem.width, root.anchorItem.height)
        const anchorCenterX = anchorLeft.x + (anchorRight.x - anchorLeft.x) / 2

        let nextX = anchorBottomRight.x - root.width
        let nextY = anchorBottomLeft.y + root.anchorMargin

        if (root.placement === "below-left") {
            nextX = anchorBottomLeft.x
        } else if (root.placement === "below-center") {
            nextX = anchorCenterX - (root.width / 2)
        } else if (root.placement === "above-center") {
            nextX = anchorCenterX - (root.width / 2)
            nextY = anchorLeft.y - root.height - root.anchorMargin
        } else if (root.placement === "above-right") {
            nextX = anchorBottomRight.x - root.width
            nextY = anchorLeft.y - root.height - root.anchorMargin
        } else if (root.placement === "above-left") {
            nextX = anchorBottomLeft.x
            nextY = anchorLeft.y - root.height - root.anchorMargin
        }

        if (root.clampToParent) {
            const parentWidth = root.parent.width || 0
            const parentHeight = root.parent.height || 0
            const minX = root.minimumMargin
            const minY = root.minimumMargin
            const maxX = Math.max(minX, parentWidth - root.width - root.minimumMargin)
            const maxY = Math.max(minY, parentHeight - root.height - root.minimumMargin)
            nextX = Math.min(Math.max(nextX, minX), maxX)
            nextY = Math.min(Math.max(nextY, minY), maxY)
        }

        root.x = Math.round(nextX)
        root.y = Math.round(nextY)
    }

    onAboutToShow: Qt.callLater(root.reposition)
    onAnchorItemChanged: {
        if (root.visible) {
            Qt.callLater(root.reposition)
        }
    }
    onWidthChanged: {
        if (root.visible) {
            Qt.callLater(root.reposition)
        }
    }
    onHeightChanged: {
        if (root.visible) {
            Qt.callLater(root.reposition)
        }
    }
}

