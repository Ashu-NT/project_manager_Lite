import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

// ─────────────────────────────────────────────────────────────────────────────
// LazySectionLoader  —  lazy-loads a visible section component on demand.
//
// While the async Loader is loading (`status === Loader.Loading`), a compact
// professional loading placeholder is shown automatically.
//
// Usage (unchanged from before):
//   AppWidgets.LazySectionLoader {
//       anchors.left: parent.left
//       anchors.right: parent.right
//       active: root._idx === 2
//       loadingMessage: "Loading assignments..."   // ← optional, new
//       sourceComponent: Component { ... }
//   }
// ─────────────────────────────────────────────────────────────────────────────

Item {
    id: root

    // ── Existing public API (unchanged) ────────────────────────────────────────
    property bool      active:          false
    property bool      keepLoaded:      false
    property Component sourceComponent: null

    readonly property var  item:   _loader.item
    readonly property bool loaded: _loader.status === Loader.Ready

    // ── New public API ─────────────────────────────────────────────────────────
    // Message shown while the component is being async-loaded.
    // Leave empty to show only the spinner.
    property string loadingMessage:       ""
    // Minimum height reserved while the section is loading.
    // Prevents zero-height collapse before the section content arrives.
    property int    fallbackLoadingHeight: Theme.AppTheme.normalRowHeight * 2

    // ── Internal ───────────────────────────────────────────────────────────────
    readonly property bool _shouldLoad: root.active || (root.keepLoaded && root._loadedOnce)
    readonly property bool _isLoading:  root._shouldLoad && _loader.status === Loader.Loading

    property bool _loadedOnce:            false
    property real _measuredImplicitHeight: 0
    property int _lastLoggedStatus: Loader.Null

    width: parent ? parent.width : 0

    // Height: while loading → show fallback so layout doesn't collapse to zero;
    //         after load    → measured content height; inactive → zero.
    implicitHeight: {
        if (!root._shouldLoad)  return 0
        if (root._isLoading)    return root.fallbackLoadingHeight
        return root._measuredImplicitHeight
    }

    // ── Height measurement ─────────────────────────────────────────────────────
    function _syncMeasuredHeight() {
        if (!root._shouldLoad || !_loader.item) {
            root._measuredImplicitHeight = 0
            return
        }
        const loaderHeight = Number(_loader.implicitHeight || 0)
        const itemHeight   = Number(_loader.item.implicitHeight || 0)
        root._measuredImplicitHeight = Math.max(loaderHeight, itemHeight, 0)
    }

    onActiveChanged:     Qt.callLater(root._syncMeasuredHeight)
    onKeepLoadedChanged: Qt.callLater(root._syncMeasuredHeight)
    onWidthChanged:      Qt.callLater(root._syncMeasuredHeight)

    // ── Async loader ───────────────────────────────────────────────────────────
    Loader {
        id: _loader
        anchors.left:  parent.left
        anchors.right: parent.right
        anchors.top:   parent.top
        active:          root._shouldLoad
        visible:         root.active && !root._isLoading
        asynchronous:    true
        sourceComponent: root.sourceComponent

        onLoaded: {
            root._loadedOnce = true
            console.debug("LazySectionLoader loaded", root.loadingMessage || "<unnamed>")
            Qt.callLater(root._syncMeasuredHeight)
        }
        onStatusChanged: {
            if (_loader.status !== root._lastLoggedStatus) {
                root._lastLoggedStatus = _loader.status
                if (_loader.status === Loader.Loading) {
                    console.debug("LazySectionLoader loading", root.loadingMessage || "<unnamed>")
                } else if (_loader.status === Loader.Error) {
                    console.warn("LazySectionLoader failed", root.loadingMessage || "<unnamed>")
                }
            }
            Qt.callLater(root._syncMeasuredHeight)
        }
    }

    Connections {
        target: _loader.item
        ignoreUnknownSignals: true
        function onImplicitHeightChanged() { Qt.callLater(root._syncMeasuredHeight) }
        function onHeightChanged()         { Qt.callLater(root._syncMeasuredHeight) }
    }

    // ── Loading placeholder ────────────────────────────────────────────────────
    // Shown while `_loader` is actively loading the async component.
    // Hidden immediately once loading completes.
    Item {
        id: _loadingPlaceholder
        anchors.left:  parent.left
        anchors.right: parent.right
        anchors.top:   parent.top
        height:        root.fallbackLoadingHeight
        visible:       root._isLoading

        Row {
            anchors.left:          parent.left
            anchors.leftMargin:    Theme.AppTheme.marginMd
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.AppTheme.spacingSm

            BusyIndicator {
                anchors.verticalCenter: parent.verticalCenter
                running:        root._isLoading
                implicitWidth:  Theme.AppTheme.iconLg
                implicitHeight: Theme.AppTheme.iconLg
            }

            AppControls.Label {
                visible:            root.loadingMessage.length > 0
                anchors.verticalCenter: parent.verticalCenter
                text:               root.loadingMessage
                color:              Theme.AppTheme.textMuted
                font.family:        Theme.AppTheme.fontFamily
                font.pixelSize:     Theme.AppTheme.smallSize
            }
        }
    }
}
