import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls

// Full-workspace-area detail page.
// Shown in place of the table view when a record is opened.
// Put the workspace's detail panel as a child — it fills the content area.
//
// Usage (inside the table container Item):
//   AppWidgets.RecordDetailPage {
//       id: detailPage
//       anchors.fill: parent
//       title: selectedModel.title
//       open: false
//       onBackRequested: detailPage.open = false
//       onEditRequested: dialogHost.openEditDialog(selectedModel)
//       onDeleteRequested: dialogHost.openDeleteDialog(selectedModel)
//       XxxDetailPanel { anchors.fill: parent; ... }
//   }
Item {
    id: root

    property bool open: false
    property string title: ""
    property bool isBusy: false
    property bool showEdit: true
    property bool showDelete: true

    signal backRequested()
    signal editRequested()
    signal deleteRequested()

    default property alias content: contentSlot.data

    visible: root.open

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.surface

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // ── Header ────────────────────────────────────────────────
            Rectangle {
                Layout.fillWidth: true
                height: 44
                color: Theme.AppTheme.surfaceAlt

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: Theme.AppTheme.border
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.AppTheme.spacingMd
                    anchors.rightMargin: Theme.AppTheme.spacingMd
                    spacing: Theme.AppTheme.spacingSm

                    // Back button
                    Item {
                        id: backBtn
                        implicitWidth: backRow.implicitWidth + 12
                        implicitHeight: 28

                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.AppTheme.radiusSm
                            color: backHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"
                            border.color: backHover.containsMouse ? Theme.AppTheme.subtleBorder : "transparent"
                            border.width: 1
                        }

                        Row {
                            id: backRow
                            anchors.centerIn: parent
                            spacing: 4

                            AppIcons.AppIcon {
                                name: "chevron_left"
                                size: 12
                                iconColor: Theme.AppTheme.textSecondary
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: "Back"
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        MouseArea {
                            id: backHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.backRequested()
                        }
                    }

                    Rectangle {
                        width: 1
                        height: 18
                        color: Theme.AppTheme.divider
                    }

                    Label {
                        Layout.fillWidth: true
                        text: root.title
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    AppControls.SecondaryButton {
                        text: "Edit"
                        visible: root.showEdit
                        enabled: !root.isBusy
                        implicitWidth: 60
                        onClicked: root.editRequested()
                    }

                    AppControls.SecondaryButton {
                        text: "Delete"
                        visible: root.showDelete
                        enabled: !root.isBusy
                        implicitWidth: 66
                        onClicked: root.deleteRequested()
                    }
                }
            }

            // ── Content area ──────────────────────────────────────────
            Item {
                id: contentSlot
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
}
