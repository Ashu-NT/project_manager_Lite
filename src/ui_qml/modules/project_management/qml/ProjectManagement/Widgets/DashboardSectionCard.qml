pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property string emptyState: ""
    property var items: []

    implicitWidth: 420
    implicitHeight: sectionLayout.implicitHeight

    ColumnLayout {
        id: sectionLayout
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            visible: root.title.length > 0 || root.subtitle.length > 0
            Layout.bottomMargin: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                visible: root.title.length > 0
                text: root.title
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
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

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.items.length === 0 && root.emptyState.length > 0
            title: root.emptyState
        }

        Repeater {
            model: root.items

            delegate: ColumnLayout {
                id: sectionItem
                required property var modelData

                readonly property string statusText: String(sectionItem.modelData.statusLabel || "")
                readonly property string subtitleText: String(sectionItem.modelData.subtitle || "")
                readonly property string supportingText: String(sectionItem.modelData.supportingText || "")
                readonly property string metaText: String(sectionItem.modelData.metaText || "")

                Layout.fillWidth: true
                spacing: 2

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: Theme.AppTheme.spacingXs
                    Layout.bottomMargin: Theme.AppTheme.spacingXs
                    spacing: Theme.AppTheme.spacingXs

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        Label {
                            Layout.fillWidth: true
                            text: String(sectionItem.modelData.title || "")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            elide: Text.ElideRight
                        }

                        AppWidgets.StatusChip {
                            visible: sectionItem.statusText.length > 0
                            status: sectionItem.statusText
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: sectionItem.subtitleText.length > 0
                        text: sectionItem.subtitleText
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        elide: Text.ElideRight
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: sectionItem.supportingText.length > 0
                        text: sectionItem.supportingText
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        elide: Text.ElideRight
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: sectionItem.metaText.length > 0
                        text: sectionItem.metaText
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        elide: Text.ElideRight
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.AppTheme.divider
                }
            }
        }
    }
}
