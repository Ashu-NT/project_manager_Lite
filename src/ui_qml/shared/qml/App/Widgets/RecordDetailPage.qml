import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls

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
        color: Theme.AppTheme.workspaceBackground

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.AppTheme.panelHeaderHeight
                color: Theme.AppTheme.surfaceRaised

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: Theme.AppTheme.divider
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    Item {
                        id: backButton
                        implicitWidth: backRow.implicitWidth + 14
                        implicitHeight: Theme.AppTheme.inputHeight

                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.AppTheme.radiusSm
                            color: backHover.containsMouse
                                ? Theme.AppTheme.hoverSurface
                                : Theme.AppTheme.surfaceOverlay
                        }

                        Row {
                            id: backRow
                            anchors.centerIn: parent
                            spacing: Theme.AppTheme.spacingXs

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
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
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
                        implicitWidth: 1
                        implicitHeight: 18
                        color: Theme.AppTheme.divider
                    }

                    Label {
                        Layout.fillWidth: true
                        text: root.title
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.sectionSize
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    AppControls.SecondaryButton {
                        text: "Edit"
                        visible: root.showEdit
                        enabled: !root.isBusy
                        implicitWidth: 72
                        onClicked: root.editRequested()
                    }

                    AppControls.SecondaryButton {
                        text: "Delete"
                        visible: root.showDelete
                        enabled: !root.isBusy
                        implicitWidth: 80
                        danger: true
                        onClicked: root.deleteRequested()
                    }
                }
            }

            Item {
                id: contentSlot
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
}
