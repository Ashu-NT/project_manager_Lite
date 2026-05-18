pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// Column visibility popup for DataTable.
// Pass in `columns` (same array as DataTable), listen to columnVisibilityChanged.
Popup {
    id: root

    property var columns: []

    signal columnVisibilityChanged(var updatedColumns)

    width: 260
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

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
        color: Theme.AppTheme.surface
        border.width: 1

        layer.enabled: true
        layer.effect: null
    }

    contentItem: ColumnLayout {
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            height: 40
            color: Theme.AppTheme.surfaceAlt
            radius: Theme.AppTheme.radiusMd

            Label {
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
            height: 1
            color: Theme.AppTheme.divider
        }

        // Column list
        Flickable {
            Layout.fillWidth: true
            implicitHeight: Math.min(colList.implicitHeight, 280)
            contentHeight: colList.implicitHeight
            clip: true

            ColumnLayout {
                id: colList
                width: parent.width
                spacing: 0

                Repeater {
                    model: root._draft

                    delegate: Rectangle {
                        id: checkRow
                        required property var modelData
                        required property int index

                        Layout.fillWidth: true
                        height: 36
                        color: checkRowHover.containsMouse
                            ? Theme.AppTheme.hoverSurface
                            : "transparent"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.AppTheme.marginMd
                            anchors.rightMargin: Theme.AppTheme.marginMd
                            spacing: Theme.AppTheme.spacingSm

                            CheckBox {
                                id: colCheck
                                checked: checkRow.modelData.visible
                                onCheckedChanged: {
                                    const updated = []
                                    for (let i = 0; i < root._draft.length; i++) {
                                        const col = root._draft[i]
                                        updated.push({
                                            key: col.key,
                                            label: col.label,
                                            visible: i === checkRow.index ? colCheck.checked : col.visible
                                        })
                                    }
                                    root._draft = updated
                                }
                            }

                            Label {
                                Layout.fillWidth: true
                                text: checkRow.modelData.label || checkRow.modelData.key
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                elide: Text.ElideRight
                            }
                        }

                        MouseArea {
                            id: checkRowHover
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: colCheck.toggle()
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
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
                implicitWidth: 70
                onClicked: root.close()
            }

            AppControls.PrimaryButton {
                text: "Apply"
                implicitWidth: 70
                onClicked: {
                    root.columnVisibilityChanged(root._draft)
                    root.close()
                }
            }
        }
    }
}
