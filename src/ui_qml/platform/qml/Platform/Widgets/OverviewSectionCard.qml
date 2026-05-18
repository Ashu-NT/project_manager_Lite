pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Item {
    id: root

    property string title: ""
    property string emptyState: ""
    property var rows: []

    implicitWidth: 320
    implicitHeight: sectionLayout.implicitHeight

    ColumnLayout {
        id: sectionLayout
        anchors.fill: parent
        spacing: 0

        Label {
            Layout.fillWidth: true
            Layout.bottomMargin: Theme.AppTheme.spacingSm
            text: root.title
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            visible: root.rows.length === 0 && root.emptyState.length > 0
            text: root.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.rows

            delegate: ColumnLayout {
                id: sectionRow
                required property var modelData

                Layout.fillWidth: true
                spacing: 2

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.topMargin: Theme.AppTheme.spacingXs
                    Layout.bottomMargin: Theme.AppTheme.spacingXs
                    spacing: 2

                    Label {
                        Layout.fillWidth: true
                        text: sectionRow.modelData.label
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Label {
                        Layout.fillWidth: true
                        text: sectionRow.modelData.value
                        color: Theme.AppTheme.accent
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Label {
                        Layout.fillWidth: true
                        text: sectionRow.modelData.supportingText
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
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
