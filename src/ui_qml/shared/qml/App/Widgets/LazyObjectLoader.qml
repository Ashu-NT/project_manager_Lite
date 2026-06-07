import QtQuick

Item {
    id: root

    property Component sourceComponent: null

    readonly property var item: _loader.item
    readonly property bool loaded: _loader.status === Loader.Ready

    property string _pendingMethod: ""
    property var _pendingArgs: []
    property int _lastLoggedStatus: Loader.Null

    width: 0
    height: 0
    visible: false

    function ensureLoaded() {
        console.debug("LazyObjectLoader ensureLoaded requested")
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
        console.debug("LazyObjectLoader invocation queued", method)
        if (_loader.status === Loader.Ready && _loader.item) {
            Qt.callLater(root._flushInvocation)
        }
    }

    function _flushInvocation() {
        if (!_loader.item || !root._pendingMethod.length) {
            return
        }

        const methodName = root._pendingMethod
        const method = _loader.item[methodName]
        const args = root._pendingArgs || []
        root._pendingMethod = ""
        root._pendingArgs = []

        if (typeof method === "function") {
            console.debug("LazyObjectLoader invoking", methodName)
            method.apply(_loader.item, args)
        } else {
            console.warn("LazyObjectLoader missing method", methodName)
        }
    }

    Loader {
        id: _loader
        active: false
        asynchronous: true
        visible: false
        sourceComponent: root.sourceComponent

        onLoaded: {
            console.debug("LazyObjectLoader loaded")
            Qt.callLater(root._flushInvocation)
        }
        onStatusChanged: {
            if (_loader.status !== root._lastLoggedStatus) {
                root._lastLoggedStatus = _loader.status
                if (_loader.status === Loader.Loading) {
                    console.debug("LazyObjectLoader loading")
                } else if (_loader.status === Loader.Error) {
                    console.warn("LazyObjectLoader failed")
                }
            }
        }
    }
}
