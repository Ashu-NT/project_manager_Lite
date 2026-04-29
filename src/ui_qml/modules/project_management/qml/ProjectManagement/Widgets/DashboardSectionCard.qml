pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    property string emptyState: ""
    property var items: []

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitWidth: 420
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs
            visible: root.title.length > 0 || root.subtitle.length > 0

            Label {
                Layout.fillWidth: true
                visible: root.title.length > 0
                text: root.title
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                visible: root.subtitle.length > 0
                text: root.subtitle
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        Label {
            Layout.fillWidth: true
            visible: root.items.length === 0 && root.emptyState.length > 0
            text: root.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.items

            delegate: Rectangle {
                id: sectionItem

                required property var modelData
                property string statusText: String(sectionItem.modelData.statusLabel || "")
                property string subtitleText: String(sectionItem.modelData.subtitle || "")
                property string supportingTextValue: String(sectionItem.modelData.supportingText || "")
                property string metaTextValue: String(sectionItem.modelData.metaText || "")

                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                border.color: Theme.AppTheme.border
                implicitHeight: itemColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)

                ColumnLayout {
                    id: itemColumn

                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingXs

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        Label {
                            Layout.fillWidth: true
                            text: sectionItem.modelData.title
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        Rectangle {
                            visible: sectionItem.statusText.length > 0
                            radius: Theme.AppTheme.radiusMd
                            color: Theme.AppTheme.accentSoft
                            border.color: Theme.AppTheme.accent
                            implicitHeight: 28
                            implicitWidth: statusLabel.implicitWidth + (Theme.AppTheme.marginMd * 2)

                            Label {
                                id: statusLabel

                                anchors.centerIn: parent
                                text: sectionItem.statusText
                                color: Theme.AppTheme.accent
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: sectionItem.subtitleText.length > 0
                        text: sectionItem.subtitleText
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: sectionItem.supportingTextValue.length > 0
                        text: sectionItem.supportingTextValue
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: sectionItem.metaTextValue.length > 0
                        text: sectionItem.metaTextValue
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
}
