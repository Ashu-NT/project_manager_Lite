pragma ComponentBehavior: Bound
import App.Controls 1.0 as AppControls

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    property var headerActions: []
    default property alias content: bodyColumn.data

    signal headerActionTriggered(string actionId)

    radius: Theme.AppTheme.radiusMd
    color: Theme.AppTheme.surfaceRaised
    border.color: Theme.AppTheme.subtleBorder
    border.width: 1
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: visible
                ? headerColumn.implicitHeight + (Theme.AppTheme.spacingSm * 2)
                : 0
            visible: root.title.length > 0 || root.subtitle.length > 0 || root.headerActions.length > 0
            color: Qt.rgba(0, 0, 0, 0)

            ColumnLayout {
                id: headerColumn

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                anchors.topMargin: Theme.AppTheme.spacingSm
                spacing: 2

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: root.title.length > 0
                        text: root.title
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                        font.letterSpacing: 0.5
                        elide: Text.ElideRight
                    }

                    Repeater {
                        model: root.headerActions

                        delegate: Rectangle {
                            id: _actionRect
                            required property var modelData

                            implicitWidth: _actionLabel.implicitWidth + 14
                            implicitHeight: 24
                            radius: Theme.AppTheme.radiusSm
                            color: _actionHover.containsMouse
                                ? Theme.AppTheme.hoverSurface
                                : Theme.AppTheme.surfaceOverlay

                            AppControls.Label {
                                id: _actionLabel
                                anchors.centerIn: parent
                                text: String(_actionRect.modelData.label || "")
                                color: Theme.AppTheme.accent
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            MouseArea {
                                id: _actionHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.headerActionTriggered(String(_actionRect.modelData.id || ""))
                            }
                        }
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: root.subtitle.length > 0
                    text: root.subtitle
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Theme.AppTheme.divider
            }
        }

        ColumnLayout {
            id: bodyColumn
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.AppTheme.spacingSm
        }
    }
}

