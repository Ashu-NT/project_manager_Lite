pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property string emptyTitle: "No record selected"
    property string primaryActionLabel: "Edit"
    property string secondaryActionLabel: "Toggle Active"
    property string primaryActionIcon: "edit"
    property string secondaryActionIcon: "workflow"
    property var detailModel: AppMock.MockFactory.detail()
    property bool isBusy: false

    signal primaryActionRequested()
    signal secondaryActionRequested()

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: root.detailModel.id ? (root.detailModel.title || root.emptyTitle) : root.emptyTitle
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: root.detailModel.subtitle || root.detailModel.emptyState || ""
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            AppWidgets.StatusChip {
                visible: String(root.detailModel.statusLabel || "").length > 0
                status: root.detailModel.statusLabel || ""
            }
        }

        Label {
            Layout.fillWidth: true
            visible: !root.detailModel.id && String(root.detailModel.emptyState || "").length > 0
            text: root.detailModel.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: !!root.detailModel.id
            text: root.detailModel.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.detailModel.fields || []

            delegate: Item {
                id: fieldRow
                required property var modelData

                Layout.fillWidth: true
                implicitHeight: fieldLayout.implicitHeight + Theme.AppTheme.spacingMd + 1

                ColumnLayout {
                    id: fieldLayout

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.leftMargin: Theme.AppTheme.spacingSm
                    anchors.rightMargin: Theme.AppTheme.spacingSm
                    anchors.topMargin: Theme.AppTheme.spacingSm
                    spacing: Theme.AppTheme.spacingXs

                    Label {
                        Layout.fillWidth: true
                        text: String(fieldRow.modelData.label || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }

                    Label {
                        Layout.fillWidth: true
                        text: String(fieldRow.modelData.value || "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: String(fieldRow.modelData.supportingText || "").length > 0
                        text: String(fieldRow.modelData.supportingText || "")
                        color: Theme.AppTheme.textSecondary
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
        }

        RowLayout {
            Layout.fillWidth: true
            visible: !!root.detailModel.id
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                visible: root.primaryActionLabel.length > 0
                text: root.primaryActionLabel
                iconName: root.primaryActionIcon
                enabled: !root.isBusy && !!(root.detailModel.state && root.detailModel.state.canPrimaryAction)
                onClicked: root.primaryActionRequested()
            }

            AppControls.SecondaryButton {
                visible: root.secondaryActionLabel.length > 0
                text: root.secondaryActionLabel
                iconName: root.secondaryActionIcon
                enabled: !root.isBusy && !!(root.detailModel.state && root.detailModel.state.canSecondaryAction)
                onClicked: root.secondaryActionRequested()
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }
}
