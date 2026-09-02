pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

QQC2.Control {
    id: root

    property string placeholderText: "Select..."
    property string searchPlaceholder: "Search..."
    property string selectedId: ""
    property string selectedLabel: ""
    property string contextKey: ""
    property int pageSize: 25
    property bool allowEmpty: false
    property string emptyLabel: "None"
    property bool lookupBusy: false
    property string lookupError: ""
    property var items: []
    property int currentPage: 1
    property int total: 0
    property bool hasMore: false
    property int _generation: 0

    signal lookupRequested(string query, int page, int pageSize, int generation, string contextKey)
    signal selectionChanged(string value, string label)

    implicitHeight: Theme.AppTheme.inputHeight
    implicitWidth: 260
    Layout.minimumWidth: 0
    padding: 0
    focusPolicy: Qt.StrongFocus

    function openPopup() {
        if (!root.enabled) return
        selectorPopup.open()
    }

    function requestLookup(page) {
        const requestedPage = Math.max(1, Number(page || 1))
        root._generation += 1
        root.lookupBusy = true
        root.lookupError = ""
        root.lookupRequested(
            searchField.text,
            requestedPage,
            root.pageSize,
            root._generation,
            root.contextKey
        )
    }

    function acceptResult(result, generation, responseContextKey) {
        if (Number(generation) !== root._generation
                || String(responseContextKey || "") !== root.contextKey) return false
        root.lookupBusy = false
        if (!result || !result.ok) {
            root.items = []
            root.total = 0
            root.hasMore = false
            root.lookupError = String((result && result.message) || "Unable to load options.")
            return false
        }
        const acceptedPage = Math.max(1, Number(result.page || 1))
        const acceptedItems = result.items || []
        root.items = acceptedPage > 1
            ? root._appendUniqueItems(root.items, acceptedItems)
            : acceptedItems
        root.currentPage = acceptedPage
        root.total = Math.max(0, Number(result.total || 0))
        root.hasMore = Boolean(result.hasMore)
        root.lookupError = ""
        return true
    }

    function _appendUniqueItems(existingItems, nextItems) {
        const merged = (existingItems || []).slice()
        const knownValues = {}
        for (let i = 0; i < merged.length; i += 1)
            knownValues[String(merged[i].value || "")] = true
        for (let j = 0; j < (nextItems || []).length; j += 1) {
            const item = nextItems[j]
            const value = String(item.value || "")
            if (!knownValues[value]) {
                knownValues[value] = true
                merged.push(item)
            }
        }
        return merged
    }

    function setResolvedItem(item) {
        if (!item) return
        root.selectedId = String(item.value || "")
        root.selectedLabel = String(item.label || "")
    }

    function clearSelection() {
        root._generation += 1
        root.selectedId = ""
        root.selectedLabel = ""
        root.items = []
        root.currentPage = 1
        root.total = 0
        root.hasMore = false
        root.lookupBusy = false
        root.lookupError = ""
        searchField.text = ""
    }

    function selectItem(item) {
        if (!item) return
        const value = String(item.value || "")
        const label = String(item.label || "")
        root.selectedId = value
        root.selectedLabel = label
        root.selectionChanged(value, label)
        selectorPopup.close()
    }

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Space || event.key === Qt.Key_Down || event.key === Qt.Key_Return) {
            root.openPopup()
            event.accepted = true
        }
    }

    contentItem: RowLayout {
        spacing: Theme.AppTheme.spacingXs

        Text {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.spacingSm + 2
            text: root.selectedLabel || root.placeholderText
            color: root.selectedLabel
                ? (root.enabled ? Theme.AppTheme.textPrimary : Theme.AppTheme.textMuted)
                : Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        QQC2.BusyIndicator {
            visible: root.lookupBusy
            running: visible
            Layout.preferredWidth: Theme.AppTheme.toolbarIconSize
            Layout.preferredHeight: Theme.AppTheme.toolbarIconSize
        }

        AppIcons.AppIcon {
            Layout.rightMargin: Theme.AppTheme.spacingSm
            name: "chevron_down"
            size: Theme.AppTheme.toolbarIconSize
            iconColor: Theme.AppTheme.textMuted
        }
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusSm
        color: root.enabled ? Theme.AppTheme.surfaceRaised : Theme.AppTheme.surfaceOverlay
        border.width: 1
        border.color: root.activeFocus
            ? Theme.AppTheme.focusBorder
            : hover.hovered ? Theme.AppTheme.borderStrong : Theme.AppTheme.subtleBorder

        HoverHandler { id: hover }
        TapHandler { enabled: root.enabled; onTapped: root.openPopup() }
    }

    QQC2.Popup {
        id: selectorPopup
        y: root.height + Theme.AppTheme.spacingXs
        width: Math.max(root.width, 320)
        height: Math.min(420, contentColumn.implicitHeight + (padding * 2))
        padding: Theme.AppTheme.spacingSm
        closePolicy: QQC2.Popup.CloseOnEscape | QQC2.Popup.CloseOnPressOutside

        onOpened: {
            searchField.forceActiveFocus()
            root.requestLookup(1)
        }

        background: Rectangle {
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.width: 1
            border.color: Theme.AppTheme.dialogBorder
        }

        contentItem: ColumnLayout {
            id: contentColumn
            spacing: Theme.AppTheme.spacingSm

            SearchField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: root.searchPlaceholder
                debounceInterval: 280
                onSearchTriggered: root.requestLookup(1)
                Keys.onDownPressed: resultList.forceActiveFocus()
            }

            Label {
                Layout.fillWidth: true
                visible: root.lookupError.length > 0
                text: root.lookupError
                color: Theme.AppTheme.danger
                wrapMode: Text.Wrap
            }

            ListView {
                id: resultList
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(260, Math.max(48, contentHeight))
                clip: true
                model: root.items
                currentIndex: -1
                boundsBehavior: Flickable.StopAtBounds
                keyNavigationEnabled: true
                activeFocusOnTab: true
                Keys.onReturnPressed: root.selectItem(root.items[currentIndex])
                Keys.onEnterPressed: root.selectItem(root.items[currentIndex])
                QQC2.ScrollBar.vertical: QQC2.ScrollBar {}

                onContentYChanged: {
                    const nearEnd = contentHeight > height
                        && contentY + height >= contentHeight - 48
                    if (nearEnd && root.hasMore && !root.lookupBusy)
                        root.requestLookup(root.currentPage + 1)
                }

                header: QQC2.ItemDelegate {
                    width: resultList.width
                    height: root.allowEmpty ? implicitHeight : 0
                    visible: root.allowEmpty
                    text: root.emptyLabel
                    onClicked: {
                        root.selectedId = ""
                        root.selectedLabel = root.emptyLabel
                        root.selectionChanged("", root.emptyLabel)
                        selectorPopup.close()
                    }
                }

                delegate: QQC2.ItemDelegate {
                    id: optionDelegate
                    required property var modelData
                    width: resultList.width
                    text: String(optionDelegate.modelData.label || "")
                    highlighted: String(optionDelegate.modelData.value || "") === root.selectedId
                    onClicked: root.selectItem(optionDelegate.modelData)
                }

                Label {
                    anchors.centerIn: parent
                    visible: !root.lookupBusy && root.lookupError.length === 0 && root.items.length === 0
                    text: "No matching options"
                    color: Theme.AppTheme.textMuted
                }
            }

            RowLayout {
                Layout.fillWidth: true

                Label {
                    Layout.fillWidth: true
                    text: root.total > 0
                        ? root.items.length + " of " + root.total + " results"
                        : "0 results"
                    color: Theme.AppTheme.textMuted
                }

                QQC2.BusyIndicator {
                    visible: root.lookupBusy && root.currentPage > 1
                    running: visible
                    Layout.preferredWidth: Theme.AppTheme.toolbarIconSize
                    Layout.preferredHeight: Theme.AppTheme.toolbarIconSize
                }
            }
        }
    }
}
