pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// Column visibility popup for DataTable.
// Pass in `columns` (same array as DataTable), listen to columnVisibilityChanged.
AnchoredPopup {
    id: root

    property var columns: []

    signal columnVisibilityChanged(var updatedColumns)

    width: Math.min(300, Theme.AppTheme.dialogCompactWidth)
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    placement: "below-right"

    // Internal draft state — committed on Apply
    property var _draft: []

    onAboutToShow: {
        const copy = []
        for (let i = 0; i < root.columns.length; i++) {
            const col = root.columns[i]
            copy.push({ key: col.key, label: col.label, visible: col.visible !== false })
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
            Layout.preferredHeight: Math.min(contentHeight, 280)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root._draft

            delegate: Rectangle {
                id: checkRow
                required property var modelData
                required property int index

                width: _colList.width
                height: Theme.AppTheme.normalRowHeight
                color: _checkRowHover.containsMouse
                    ? Theme.AppTheme.hoverSurface
                    : "transparent"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin:  Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.CheckBox {
                        id: _colCheck
                        checked: checkRow.modelData.visible
                        onToggled: {
                            root._draft[checkRow.index].visible = checked
                        }
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text:           checkRow.modelData.label || checkRow.modelData.key
                        color:          Theme.AppTheme.textPrimary
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        elide:          Text.ElideRight
                    }
                }

                MouseArea {
                    id: _checkRowHover
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: _colCheck.toggle()
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
            Layout.leftMargin: Theme.AppTheme.marginMd
            Layout.rightMargin: Theme.AppTheme.marginMd
            Layout.topMargin: Theme.AppTheme.spacingSm
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
                        reset.push({
                            key: col.key,
                            label: col.label,
                            visible: col.visibleByDefault !== false
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
