pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

// Column visibility + reorder popup for DataTable.
// Pass in `columns` (same array as DataTable, may include required/configurable flags).
// Emits columnVisibilityChanged with ordered draft on Apply.
AnchoredPopup {
    id: root

    property var columns: []

    signal columnVisibilityChanged(var updatedColumns)

    width: Math.min(340, Theme.AppTheme.dialogCompactWidth)
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    placement: "below-right"

    // Internal draft — only configurable columns, in user-controlled order
    property var _draft: []

    function _moveUp(idx) {
        if (idx <= 0) return
        const arr = root._draft.slice()
        const tmp = arr[idx - 1]
        arr[idx - 1] = arr[idx]
        arr[idx] = tmp
        root._draft = arr
    }

    function _moveDown(idx) {
        if (idx >= root._draft.length - 1) return
        const arr = root._draft.slice()
        const tmp = arr[idx + 1]
        arr[idx + 1] = arr[idx]
        arr[idx] = tmp
        root._draft = arr
    }

    onAboutToShow: {
        const copy = []
        for (let i = 0; i < root.columns.length; i++) {
            const col = root.columns[i]
            if (col.configurable === false) continue
            copy.push({
                key:      col.key,
                label:    col.label,
                visible:  col.visible !== false,
                required: col.required === true
            })
        }
        root._draft = copy
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusMd
        color: Theme.AppTheme.dialogBackground
        border.color: Theme.AppTheme.dialogBorder
        border.width: 1

        layer.enabled: true
        layer.effect: null
    }

    contentItem: ColumnLayout {
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.AppTheme.dialogHeaderHeight
            color: Theme.AppTheme.dialogHeaderBackground
            radius: Theme.AppTheme.radiusMd

            AppControls.Label {
                anchors.left: parent.left
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.verticalCenter: parent.verticalCenter
                text: "Customize Columns"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        // Column list
        ListView {
            id: _colList
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, 300)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root._draft

            delegate: Rectangle {
                id: checkRow
                required property var modelData
                required property int index

                width: _colList.width
                height: Theme.AppTheme.normalRowHeight
                color: _rowHover.containsMouse
                    ? Theme.AppTheme.hoverSurface
                    : "transparent"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin:  Theme.AppTheme.spacingXs
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingXs

                    // Up / down reorder buttons
                    Button {
                        id: _upBtn
                        implicitWidth:  22
                        implicitHeight: 22
                        enabled: checkRow.index > 0
                        opacity: enabled ? 1.0 : 0.25
                        focusPolicy: Qt.NoFocus
                        background: Rectangle {
                            radius: 3
                            color: _upBtn.pressed ? Theme.AppTheme.hoverSurface : "transparent"
                        }
                        contentItem: AppIcons.AppIcon {
                            name: "chevron_up"
                            size: 13
                            iconColor: Theme.AppTheme.textSecondary
                        }
                        onClicked: root._moveUp(checkRow.index)
                    }

                    Button {
                        id: _downBtn
                        implicitWidth:  22
                        implicitHeight: 22
                        enabled: checkRow.index < root._draft.length - 1
                        opacity: enabled ? 1.0 : 0.25
                        focusPolicy: Qt.NoFocus
                        background: Rectangle {
                            radius: 3
                            color: _downBtn.pressed ? Theme.AppTheme.hoverSurface : "transparent"
                        }
                        contentItem: AppIcons.AppIcon {
                            name: "chevron_down"
                            size: 13
                            iconColor: Theme.AppTheme.textSecondary
                        }
                        onClicked: root._moveDown(checkRow.index)
                    }

                    AppControls.CheckBox {
                        id: _colCheck
                        checked: checkRow.modelData.visible
                        enabled: !checkRow.modelData.required
                        opacity: checkRow.modelData.required ? 0.55 : 1.0
                        onToggled: {
                            root._draft[checkRow.index].visible = checked
                        }
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: checkRow.modelData.label || checkRow.modelData.key
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: _rowHover
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (!checkRow.modelData.required) _colCheck.toggle()
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        // Footer actions
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin:   Theme.AppTheme.marginMd
            Layout.rightMargin:  Theme.AppTheme.marginMd
            Layout.topMargin:    Theme.AppTheme.spacingSm
            Layout.bottomMargin: Theme.AppTheme.spacingSm
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: "Reset"
                iconName: "refresh"
                implicitWidth: 70
                onClicked: {
                    const reset = []
                    for (let i = 0; i < root.columns.length; i++) {
                        const col = root.columns[i]
                        if (col.configurable === false) continue
                        reset.push({
                            key:      col.key,
                            label:    col.label,
                            visible:  col.visibleByDefault !== false,
                            required: col.required === true
                        })
                    }
                    root._draft = reset
                }
            }

            Item { Layout.fillWidth: true }

            AppControls.SecondaryButton {
                text: "Cancel"
                iconName: "close"
                implicitWidth: 70
                onClicked: root.close()
            }

            AppControls.PrimaryButton {
                text: "Apply"
                iconName: "approve"
                implicitWidth: 70
                onClicked: {
                    root.columnVisibilityChanged(root._draft)
                    root.close()
                }
            }
        }
    }
}
