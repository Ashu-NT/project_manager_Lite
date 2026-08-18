pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

QQC2.ComboBox {
    id: control

    property string placeholderText: ""
    // Long option lists (currencies, sites, managers, ...) get an in-popup
    // search box automatically; short ones (a handful of statuses) don't
    // need one. Callers can force it on/off by overriding this threshold
    // rather than each call site opting in individually.
    property int searchThreshold: 8

    property string _searchText: ""
    readonly property bool _searchEnabled: control.count > control.searchThreshold
    readonly property bool _showFilteredList: control._searchEnabled && control._searchText.length > 0
    readonly property var _filteredEntries: {
        if (!control._showFilteredList) return []
        const query = control._searchText.toLowerCase()
        const results = []
        for (let i = 0; i < control.count; i++) {
            const label = String(control.textAt(i) || "")
            if (label.toLowerCase().includes(query)) {
                results.push({ "index": i, "label": label })
            }
        }
        return results
    }

    implicitHeight: Theme.AppTheme.inputHeight
    implicitWidth: Math.max(160, contentItem.implicitWidth + Theme.AppTheme.spacingXl)
    leftPadding: Theme.AppTheme.spacingSm + 2
    rightPadding: Theme.AppTheme.spacingXl + Theme.AppTheme.spacingSm
    topPadding: 0
    bottomPadding: 0
    font.family: Theme.AppTheme.fontFamily
    font.pixelSize: Theme.AppTheme.bodySize

    contentItem: Text {
        leftPadding: 0
        rightPadding: 0
        verticalAlignment: Text.AlignVCenter
        text: control.currentIndex >= 0
            ? control.displayText
            : control.placeholderText
        color: control.currentIndex >= 0
            ? (control.enabled ? Theme.AppTheme.textPrimary : Theme.AppTheme.textMuted)
            : Theme.AppTheme.textMuted
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.bodySize
        elide: Text.ElideRight
    }

    indicator: AppIcons.AppIcon {
        anchors.right: parent.right
        anchors.rightMargin: Theme.AppTheme.spacingSm
        anchors.verticalCenter: parent.verticalCenter
        name: "chevron_down"
        size: Theme.AppTheme.toolbarIconSize
        iconColor: Theme.AppTheme.textMuted
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusSm
        color: control.enabled
            ? Theme.AppTheme.surfaceRaised
            : Theme.AppTheme.surfaceOverlay
        border.width: 1
        border.color: control.activeFocus
            ? Theme.AppTheme.focusBorder
            : control.hovered
                ? Theme.AppTheme.borderStrong
                : Theme.AppTheme.subtleBorder
    }

    delegate: QQC2.ItemDelegate {
        required property int index

        width: control.width
        highlighted: control.highlightedIndex === index
        padding: 0

        contentItem: Text {
            leftPadding: Theme.AppTheme.spacingSm + 2
            rightPadding: Theme.AppTheme.spacingSm + 2
            verticalAlignment: Text.AlignVCenter
            text: control.textAt(index)
            color: highlighted
                ? Theme.AppTheme.accent
                : Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            elide: Text.ElideRight
        }

        background: Rectangle {
            color: parent.highlighted
                ? Theme.AppTheme.selectedSurface
                : hovered
                    ? Theme.AppTheme.hoverSurface
                    : "transparent"
        }
    }

    popup: QQC2.Popup {
        id: comboPopup
        y: control.height + Theme.AppTheme.spacingXs
        width: control.width
        padding: Theme.AppTheme.spacingXs

        onOpened: control._searchText = ""
        onClosed: control._searchText = ""

        background: Rectangle {
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceRaised
            border.color: Theme.AppTheme.dialogBorder
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingXs

            SearchField {
                Layout.fillWidth: true
                Layout.bottomMargin: Theme.AppTheme.spacingXs
                visible: control._searchEnabled
                placeholderText: "Search..."
                debounceInterval: 0
                onTextEdited: (text) => { control._searchText = text }
                onAccepted: {
                    if (control._filteredEntries.length > 0) {
                        control.currentIndex = control._filteredEntries[0].index
                        control.activated(control._filteredEntries[0].index)
                        comboPopup.close()
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                Layout.topMargin: Theme.AppTheme.spacingSm
                Layout.bottomMargin: Theme.AppTheme.spacingSm
                visible: control.popup.visible && control._showFilteredList && control._filteredEntries.length === 0
                text: "No matches"
                horizontalAlignment: Text.AlignHCenter
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
            }

            ListView {
                id: filteredList
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(contentHeight, 280)
                clip: true
                visible: control.popup.visible && control._showFilteredList
                model: visible ? control._filteredEntries : null
                boundsBehavior: Flickable.StopAtBounds
                QQC2.ScrollBar.vertical: QQC2.ScrollBar { }

                delegate: QQC2.ItemDelegate {
                    id: filteredDelegate
                    required property var modelData

                    width: filteredList.width
                    padding: 0

                    contentItem: Text {
                        leftPadding: Theme.AppTheme.spacingSm + 2
                        rightPadding: Theme.AppTheme.spacingSm + 2
                        verticalAlignment: Text.AlignVCenter
                        text: String(filteredDelegate.modelData.label || "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        elide: Text.ElideRight
                    }

                    background: Rectangle {
                        color: filteredDelegate.hovered ? Theme.AppTheme.hoverSurface : "transparent"
                    }

                    onClicked: {
                        control.currentIndex = filteredDelegate.modelData.index
                        control.activated(filteredDelegate.modelData.index)
                        comboPopup.close()
                    }
                }
            }

            ListView {
                clip: true
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(contentHeight, 280)
                visible: control.popup.visible && !control._showFilteredList
                model: visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
                // Land on the current selection instantly when the popup
                // opens -- the default highlightMoveVelocity would visibly
                // glide/scroll down to it first (e.g. a long alphabetical
                // list defaulted near the end, like currencies -> XAF),
                // which reads as janky rather than a deliberate reveal.
                highlightMoveDuration: 0
                boundsBehavior: Flickable.StopAtBounds
                QQC2.ScrollBar.vertical: QQC2.ScrollBar { }
            }
        }
    }
}
