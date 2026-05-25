import QtQuick

Item {
    id: root

    property bool active: false
    property bool keepLoaded: false
    property Component sourceComponent: null

    readonly property var item: _loader.item
    readonly property bool loaded: _loader.status === Loader.Ready
    readonly property bool _shouldLoad: root.active || (root.keepLoaded && root._loadedOnce)
    property bool _loadedOnce: false
    property real _measuredImplicitHeight: 0

    width: parent ? parent.width : 0
    implicitHeight: root._shouldLoad ? root._measuredImplicitHeight : 0

    function _syncMeasuredHeight() {
        if (!root._shouldLoad || !_loader.item) {
            root._measuredImplicitHeight = 0
            return
        }

        const loaderHeight = Number(_loader.implicitHeight || 0)
        const itemHeight = Number(_loader.item.implicitHeight || 0)
        root._measuredImplicitHeight = Math.max(loaderHeight, itemHeight, 0)
    }

    onActiveChanged: Qt.callLater(root._syncMeasuredHeight)
    onKeepLoadedChanged: Qt.callLater(root._syncMeasuredHeight)
    onWidthChanged: Qt.callLater(root._syncMeasuredHeight)

    Loader {
        id: _loader
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        active: root._shouldLoad
        visible: root.active
        asynchronous: true
        sourceComponent: root.sourceComponent

        onLoaded: {
            root._loadedOnce = true
            Qt.callLater(root._syncMeasuredHeight)
        }

        onStatusChanged: Qt.callLater(root._syncMeasuredHeight)
    }

    Connections {
        target: _loader.item
        ignoreUnknownSignals: true

        function onImplicitHeightChanged() {
            Qt.callLater(root._syncMeasuredHeight)
        }

        function onHeightChanged() {
            Qt.callLater(root._syncMeasuredHeight)
        }
    }
}
