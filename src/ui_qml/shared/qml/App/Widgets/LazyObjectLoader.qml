import QtQuick

Item {
    id: root

    property Component sourceComponent: null

    readonly property var item: _loader.item
    readonly property bool loaded: _loader.status === Loader.Ready

    property string _pendingMethod: ""
    property var _pendingArgs: []

    width: 0
    height: 0
    visible: false

    function ensureLoaded() {
        _loader.active = true
    }

    function invoke(methodName, arg1, arg2, arg3, arg4) {
        const method = String(methodName || "")
        if (!method.length) {
            return
        }

        root._pendingMethod = method
        root._pendingArgs = []
        for (let index = 1; index < arguments.length; index += 1) {
            root._pendingArgs.push(arguments[index])
        }

        _loader.active = true
        if (_loader.status === Loader.Ready && _loader.item) {
            Qt.callLater(root._flushInvocation)
        }
    }

    function _flushInvocation() {
        if (!_loader.item || !root._pendingMethod.length) {
            return
        }

        const method = _loader.item[root._pendingMethod]
        const args = root._pendingArgs || []
        root._pendingMethod = ""
        root._pendingArgs = []

        if (typeof method === "function") {
            method.apply(_loader.item, args)
        }
    }

    Loader {
        id: _loader
        active: false
        asynchronous: true
        visible: false
        sourceComponent: root.sourceComponent

        onLoaded: Qt.callLater(root._flushInvocation)
    }
}
