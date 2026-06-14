pragma ComponentBehavior: Bound

import QtQuick

InlineMessage {
    id: root

    property bool requestedVisible: true
    property var detailPage: null
    property bool detailPagePinned: true

    property int _messageSectionIndex: -1
    property int _pendingSectionIndex: -1
    property var _resolvedDetailPage: null

    readonly property var _activeDetailPage: root.detailPage || root._resolvedDetailPage

    function _resolveDetailPage() {
        let current = root.parent
        while (current) {
            if (current !== root
                    && current.activeSectionIndex !== undefined
                    && current.sections !== undefined
                    && current.scrollToSection !== undefined) {
                return current
            }
            current = current.parent
        }
        return null
    }

    function _rememberCurrentSection() {
        if (!root.requestedVisible || String(root.message || "").length === 0) {
            root._messageSectionIndex = -1
            if (!root._activeDetailPage || root._activeDetailPage.isBusy !== true)
                root._pendingSectionIndex = -1
            return
        }
        const page = root._activeDetailPage
        if (!page) {
            root._messageSectionIndex = -1
            return
        }
        root._messageSectionIndex = root._pendingSectionIndex >= 0
            ? root._pendingSectionIndex
            : page.activeSectionIndex
    }

    visible: {
        if (!root.requestedVisible || String(root.message || "").length === 0)
            return false
        const page = root._activeDetailPage
        if (!page || root._messageSectionIndex < 0)
            return true
        return page.activeSectionIndex === root._messageSectionIndex
    }

    onMessageChanged: root._rememberCurrentSection()
    onRequestedVisibleChanged: root._rememberCurrentSection()
    onDetailPageChanged: root._rememberCurrentSection()
    onParentChanged: {
        if (root.detailPage === null)
            root._resolvedDetailPage = root._resolveDetailPage()
        root._rememberCurrentSection()
    }

    Connections {
        target: root._activeDetailPage
        ignoreUnknownSignals: true

        function onIsBusyChanged() {
            if (!target)
                return
            if (target.isBusy === true) {
                root._pendingSectionIndex = target.activeSectionIndex
            } else if (!root.requestedVisible || String(root.message || "").length === 0) {
                root._pendingSectionIndex = -1
            }
        }
    }

    Component.onCompleted: {
        if (root.detailPage === null)
            root._resolvedDetailPage = root._resolveDetailPage()
        Qt.callLater(root._rememberCurrentSection)
    }
}
