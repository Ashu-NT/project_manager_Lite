pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property string emptyState: ""
    property string primaryActionLabel: ""
    property string secondaryActionLabel: ""
    property string tertiaryActionLabel: ""
    property bool primaryDanger: false
    property bool secondaryDanger: false
    property bool tertiaryDanger: false
    property bool actionsEnabled: true
    property var items: []

    // Additive: row selection state
    property string selectedItemId: ""
    signal itemSelected(string itemId)

    // Preserved signals — same API as before
    signal primaryActionRequested(string itemId)
    signal secondaryActionRequested(string itemId)
    signal tertiaryActionRequested(string itemId)

    implicitWidth: 420
    implicitHeight: headerCol.implicitHeight + listCol.implicitHeight

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header — only rendered when title/subtitle present
        ColumnLayout {
            id: headerCol
            Layout.fillWidth: true
            visible: root.title.length > 0 || root.subtitle.length > 0
            spacing: Theme.AppTheme.spacingXs
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

        // Empty state
        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.items.length === 0 && root.emptyState.length > 0
            title: root.emptyState
        }

        // Row list
        ColumnLayout {
            id: listCol
            Layout.fillWidth: true
            spacing: 0

            Repeater {
                model: root.items

                delegate: Item {
                    id: rowDelegate
                    required property var modelData

                    Layout.fillWidth: true
                    height: rowContent.implicitHeight

                    readonly property bool isSelected: root.selectedItemId === String(rowDelegate.modelData.id || "")
                    readonly property string statusText: String(rowDelegate.modelData.statusLabel || "")
                    readonly property string subtitleText: String(rowDelegate.modelData.subtitle || "")
                    readonly property string metaText: String(rowDelegate.modelData.metaText || "")
                    readonly property bool hasActions: root.primaryActionLabel.length > 0
                        || root.secondaryActionLabel.length > 0
                        || root.tertiaryActionLabel.length > 0

                    // Row background — selected / hover / default
                    Rectangle {
                        anchors.fill: parent
                        color: rowDelegate.isSelected
                            ? Theme.AppTheme.selectedSurface
                            : rowHoverArea.containsMouse
                                ? Theme.AppTheme.hoverSurface
                                : "transparent"

                        // Selected accent left rail
                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: 3
                            color: Theme.AppTheme.accent
                            visible: rowDelegate.isSelected
                        }
                    }

                    ColumnLayout {
                        id: rowContent
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: rowDelegate.isSelected
                            ? Theme.AppTheme.marginMd - 3
                            : Theme.AppTheme.marginMd
                        anchors.rightMargin: Theme.AppTheme.marginMd
                        anchors.topMargin: Theme.AppTheme.spacingSm
                        anchors.bottomMargin: Theme.AppTheme.spacingSm
                        spacing: Theme.AppTheme.spacingXs

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingSm

                            Label {
                                Layout.fillWidth: true
                                text: String(rowDelegate.modelData.title || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: rowDelegate.isSelected
                                elide: Text.ElideRight
                            }

                            AppWidgets.StatusChip {
                                visible: rowDelegate.statusText.length > 0
                                status: rowDelegate.statusText
                            }
                        }

                        Label {
                            Layout.fillWidth: true
                            visible: rowDelegate.subtitleText.length > 0
                            text: rowDelegate.subtitleText
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            elide: Text.ElideRight
                        }

                        Label {
                            Layout.fillWidth: true
                            visible: rowDelegate.metaText.length > 0
                            text: rowDelegate.metaText
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            elide: Text.ElideRight
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: rowDelegate.hasActions
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.PrimaryButton {
                                visible: root.primaryActionLabel.length > 0
                                    && (rowDelegate.modelData.canPrimaryAction ?? true)
                                enabled: root.actionsEnabled
                                text: root.primaryActionLabel
                                danger: root.primaryDanger
                                onClicked: root.primaryActionRequested(String(rowDelegate.modelData.id))
                            }

                            AppControls.SecondaryButton {
                                visible: root.secondaryActionLabel.length > 0
                                    && (rowDelegate.modelData.canSecondaryAction ?? true)
                                enabled: root.actionsEnabled
                                text: root.secondaryActionLabel
                                danger: root.secondaryDanger
                                onClicked: root.secondaryActionRequested(String(rowDelegate.modelData.id))
                            }

                            AppControls.SecondaryButton {
                                visible: root.tertiaryActionLabel.length > 0
                                    && (rowDelegate.modelData.canTertiaryAction ?? true)
                                enabled: root.actionsEnabled
                                text: root.tertiaryActionLabel
                                danger: root.tertiaryDanger
                                onClicked: root.tertiaryActionRequested(String(rowDelegate.modelData.id))
                            }

                            Item { Layout.fillWidth: true }
                        }
                    }

                    // Row click — selection
                    MouseArea {
                        id: rowHoverArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            const itemId = String(rowDelegate.modelData.id || "")
                            root.selectedItemId = itemId
                            root.itemSelected(itemId)
                        }
                    }

                    // Bottom divider
                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: Theme.AppTheme.divider
                    }
                }
            }
        }
    }
}
