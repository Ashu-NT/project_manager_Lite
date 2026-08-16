pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

// Modern replacement for App.Widgets.OverviewSectionCard, scoped to
// Platform Overview only -- label/support on the left, the value emphasized
// on the right (a scannable "leaderboard row" shape), on an elevated card.
// Left as a Platform-local component rather than editing the shared widget,
// since OverviewSectionCard is still used as-is elsewhere.
Rectangle {
    id: root

    property string title: ""
    property string emptyState: ""
    property var rows: []

    implicitHeight: _layout.implicitHeight + Theme.AppTheme.marginLg * 2
    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surfaceRaised
    border.width: 1
    border.color: Theme.AppTheme.subtleBorder

    ColumnLayout {
        id: _layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingSm

        AppControls.Label {
            Layout.fillWidth: true
            Layout.bottomMargin: Theme.AppTheme.spacingXs
            text: root.title
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.sectionSize
            font.bold: true
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root.rows.length === 0 && root.emptyState.length > 0
            text: root.emptyState
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.rows

            delegate: ColumnLayout {
                id: _rowWrap
                required property var modelData
                required property int index

                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_rowWrap.modelData.label || "")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            elide: Text.ElideRight
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: String(_rowWrap.modelData.supportingText || "") !== ""
                            text: String(_rowWrap.modelData.supportingText || "")
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            elide: Text.ElideRight
                        }
                    }

                    AppControls.Label {
                        text: String(_rowWrap.modelData.value || "")
                        color: Theme.AppTheme.accent
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.sectionSize
                        font.bold: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.topMargin: Theme.AppTheme.spacingXs
                    height: 1
                    color: Theme.AppTheme.divider
                    visible: _rowWrap.index < root.rows.length - 1
                }
            }
        }
    }
}
