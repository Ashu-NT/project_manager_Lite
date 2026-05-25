import QtQuick

Item {
    id: root

    property bool active: false
    property bool keepLoaded: false
    property Component sourceComponent: null

    readonly property var item: _loader.item
    readonly property bool loaded: _loader.status === Loader.Ready
    property bool _loadedOnce: false

    width: parent ? parent.width : 0
    implicitHeight: (root.active || (root.keepLoaded && root._loadedOnce)) && _loader.item
        ? Math.max(
            Number(_loader.item.implicitHeight || 0),
            Number((_loader.item.childrenRect && _loader.item.childrenRect.height) || 0)
        )
        : 0

    Loader {
        id: _loader
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        active: root.active || (root.keepLoaded && root._loadedOnce)
        visible: root.active
        asynchronous: true
        sourceComponent: root.sourceComponent

        onLoaded: {
            root._loadedOnce = true
        }
    }
}
