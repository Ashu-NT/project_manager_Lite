pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// Centered, modal column customizer: a left "visibility" pane (checkbox +
// name, order fixed) and a right "order" pane (drag-and-drop reorder,
// hidden columns shown dimmed and undraggable but still occupying their
// slot). Both panes render the same underlying `_draft` array, so toggling
// visibility never touches array position -- a re-enabled column keeps
// whatever slot it already had.
//
// Public API (unchanged from the previous anchored-popup version):
//   columns                    [{key, label, visible, required, configurable, visibleByDefault}]
//   signal columnVisibilityChanged(var updatedColumns)
AppControls.CenteredDialog {
    id: root

    property var columns: []
    property var _draft: []
    // Index of the row currently being dragged in the order pane, or -1.
    property int _draggingIndex: -1

    signal columnVisibilityChanged(var updatedColumns)

    title: "Customize Columns"
    width: Theme.AppTheme.dialogFormWidth
    padding: 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    // Shared row height/pane height so both panes line up and scroll
    // together within the same visual bounds.
    readonly property real _paneHeight: Math.min(
        Math.max(root._draft.length, 1) * Theme.AppTheme.normalRowHeight,
        320
    )

    readonly property real maxDialogHeight: (parent ? parent.height : 760) - Theme.AppTheme.dialogPadding * 2
    height: Math.min(_shell.implicitHeight + implicitHeaderHeight + topPadding + bottomPadding, maxDialogHeight)

    function _buildDraft() {
        const copy = []
        for (let i = 0; i < root.columns.length; i++) {
            const col = root.columns[i]
            if (col.configurable === false)
                continue
            copy.push({
                key: col.key,
                label: col.label,
                visible: col.visible !== false,
                required: col.required === true
            })
        }
        return copy
    }

    // Reset restores default VISIBILITY (visibleByDefault) but, like the
    // initial draft, still starts from `root.columns`' current order --
    // it is not an "undo my reordering" action, only a visibility reset.
    function _resetDraft() {
        const reset = []
        for (let i = 0; i < root.columns.length; i++) {
            const col = root.columns[i]
            if (col.configurable === false)
                continue
            reset.push({
                key: col.key,
                label: col.label,
                visible: col.visibleByDefault !== false,
                required: col.required === true
            })
        }
        return reset
    }

    function _setVisible(index, value) {
        if (index < 0 || index >= root._draft.length)
            return
        const arr = root._draft.slice()
        arr[index] = Object.assign({}, arr[index], { visible: value })
        root._draft = arr
    }

    // ── Drag-reorder (right pane) ──────────────────────────────────────

    function _dragPress(index) {
        const col = root._draft[index]
        if (!col || col.visible !== true)
            return false
        root._draggingIndex = index
        return true
    }

    function _dragMoveTo(targetIndex) {
        if (root._draggingIndex < 0 || targetIndex === root._draggingIndex)
            return
        const arr = root._draft.slice()
        const moved = arr.splice(root._draggingIndex, 1)[0]
        arr.splice(targetIndex, 0, moved)
        root._draft = arr
        root._draggingIndex = targetIndex
    }

    function _dragRelease() {
        root._draggingIndex = -1
    }

    // ── Footer actions ─────────────────────────────────────────────────
    function _apply() {
        root.columnVisibilityChanged(root._draft)
        root.close()
    }

    function _cancel() {
        root.close()
    }

    onAboutToShow: {
        root._draggingIndex = -1
        root._draft = root._buildDraft()
    }

    contentItem: ColumnLayout {
        id: _shell
        spacing: Theme.AppTheme.spacingMd

        Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: root._paneHeight
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            spacing: Theme.AppTheme.spacingMd

            // ── LEFT — column visibility ──────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 260
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Show Columns"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.typeMetadataSize
                    font.bold: true
                }

                ListView {
                    id: _visibilityList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: root._paneHeight
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: root._draft

                    delegate: Rectangle {
                        id: visRow

                        required property var modelData
                        required property int index

                        width: _visibilityList.width
                        height: Theme.AppTheme.normalRowHeight
                        color: _visHover.hovered ? Theme.AppTheme.hoverSurface : "transparent"

                        HoverHandler { id: _visHover }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.AppTheme.spacingXs
                            anchors.rightMargin: Theme.AppTheme.marginMd
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.CheckBox {
                                // Without this, RowLayout stretches the
                                // checkbox to the full (taller) row height,
                                // but its indicator has no compensating
                                // centering of its own and renders pinned to
                                // the top -- Qt.AlignVCenter keeps it at its
                                // natural size, centered like the label.
                                Layout.alignment: Qt.AlignVCenter
                                checked: visRow.modelData.visible
                                enabled: !visRow.modelData.required
                                opacity: visRow.modelData.required ? 0.55 : 1.0
                                onToggled: root._setVisible(visRow.index, checked)
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter
                                text: visRow.modelData.label || visRow.modelData.key
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                color: Theme.AppTheme.divider
            }

            // ── RIGHT — column order ──────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 260
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Reorder Columns"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.typeMetadataSize
                    font.bold: true
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredHeight: root._paneHeight

                    ListView {
                        id: _orderList
                        anchors.fill: parent
                        clip: true
                        interactive: root._draggingIndex < 0
                        boundsBehavior: Flickable.StopAtBounds
                        model: root._draft

                        delegate: Rectangle {
                            id: ordRow

                            required property var modelData
                            required property int index

                            width: _orderList.width
                            height: Theme.AppTheme.normalRowHeight
                            radius: Theme.AppTheme.radiusSm
                            color: root._draggingIndex === ordRow.index
                                ? Theme.AppTheme.hoverSurface
                                : "transparent"
                            opacity: ordRow.modelData.visible ? 1.0 : 0.5

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.AppTheme.spacingXs
                                anchors.rightMargin: Theme.AppTheme.marginMd
                                spacing: Theme.AppTheme.spacingSm

                                // Drag-handle grip icon -- purely visual,
                                // hinting the row is draggable (the whole
                                // row is the actual drag target, see
                                // `_dragOverlay` below). Tracking lives in
                                // that stable sibling Item, not this
                                // recycled delegate, so an in-flight
                                // reorder survives the ListView recycling
                                // its delegates when `root._draft` is
                                // reassigned mid-drag.
                                Item {
                                    implicitWidth: 26
                                    implicitHeight: parent.height

                                    Grid {
                                        anchors.centerIn: parent
                                        columns: 2
                                        columnSpacing: 3
                                        rowSpacing: 3

                                        Repeater {
                                            model: 6
                                            Rectangle {
                                                width: 3; height: 3; radius: 1.5
                                                color: ordRow.modelData.visible
                                                    ? Theme.AppTheme.textMuted
                                                    : Theme.AppTheme.divider
                                            }
                                        }
                                    }
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: ordRow.modelData.label || ordRow.modelData.key
                                    color: ordRow.modelData.visible
                                        ? Theme.AppTheme.textPrimary
                                        : Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    // Claims presses landing anywhere on a visible (active)
                    // row; only hidden rows set mouse.accepted = false so
                    // the press falls through to `_orderList`'s own
                    // Flickable for normal scrolling, exactly like
                    // DataTable's own empty-space/row click-through
                    // convention.
                    MouseArea {
                        id: _dragOverlay
                        anchors.fill: _orderList
                        cursorShape: root._draggingIndex >= 0 ? Qt.SizeVerCursor : Qt.ArrowCursor

                        function _rowAt(y) {
                            const contentY = y + _orderList.contentY
                            const idx = Math.floor(contentY / Theme.AppTheme.normalRowHeight)
                            return Math.max(0, Math.min(root._draft.length - 1, idx))
                        }

                        onPressed: function(mouse) {
                            const idx = _dragOverlay._rowAt(mouse.y)
                            if (!root._dragPress(idx)) {
                                mouse.accepted = false
                            }
                        }

                        onPositionChanged: function(mouse) {
                            if (root._draggingIndex < 0)
                                return
                            root._dragMoveTo(_dragOverlay._rowAt(mouse.y))
                        }

                        onReleased: root._dragRelease()
                        onCanceled: root._dragRelease()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.dialogPadding
            Layout.rightMargin: Theme.AppTheme.dialogPadding
            Layout.bottomMargin: Theme.AppTheme.spacingSm
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: "Reset"
                iconName: "refresh"
                implicitWidth: 84
                onClicked: root._draft = root._resetDraft()
            }

            Item { Layout.fillWidth: true }

            AppControls.SecondaryButton {
                text: "Cancel"
                iconName: "close"
                implicitWidth: 84
                onClicked: root._cancel()
            }

            AppControls.PrimaryButton {
                text: "Apply"
                iconName: "approve"
                implicitWidth: 84
                onClicked: root._apply()
            }
        }
    }
}
