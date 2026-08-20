pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls


Rectangle {
    id: root

    // -- Header ---------------------------------------------------------
    property string title: ""
    property string statusLabel: ""
    property bool showHeader: true

    // -- Metadata sections ------------------------------------------------
    // Array of { label, value } sections rendered below the header, in
    // order. Entries with an empty value are hidden automatically.
    property var sections: []

    // -- Actions ----------------------------------------------------------
    property bool busy: false
    property string editActionLabel: "Edit"
    property bool showEditAction: true
    property string secondaryActionLabel: ""
    property bool showSecondaryAction: false

    // -- Extra content slot (e.g. a document preview, entity-specific
    // panel) rendered between the metadata sections and the action row.
    default property alias extraContent: _extraSlot.data

    signal closeRequested()
    signal editRequested()
    signal secondaryActionRequested()

    color: Theme.AppTheme.surface
    implicitWidth: Theme.AppTheme.inspectorWidth

    // Swallows presses on the panel's own blank background/padding so a
    // workspace page's "click outside closes the inspector" catcher never
    // sees them bleed through -- real controls (buttons, the close "X",
    // the scrollable body) are declared after this and claim their own
    // clicks first, ahead of this catch-all.
    MouseArea {
        anchors.fill: parent
    }

    Rectangle {
        anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
        width: Theme.AppTheme.borderWidthThin
        color: Theme.AppTheme.divider
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // -- Panel header -------------------------------------------------
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: root.showHeader ? Theme.AppTheme.toolbarHeight - 6 : 0
            visible: root.showHeader
            color: Theme.AppTheme.surfaceRaised

            Rectangle {
                anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                height: Theme.AppTheme.borderWidthThin
                color: Theme.AppTheme.divider
            }

            AppControls.Label {
                anchors.left: parent.left
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: _closeBtn.left
                anchors.rightMargin: 4
                text: root.title.length > 0 ? root.title : "Details"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.typeMetadataSize
                font.bold: true
                elide: Text.ElideRight
            }

            Rectangle {
                id: _closeBtn
                anchors.right: parent.right
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                width: 26; height: 26; radius: Theme.AppTheme.radiusSm
                color: _closeMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                AppIcons.AppIcon {
                    anchors.centerIn: parent
                    name: "close"
                    size: Theme.AppTheme.iconXs
                    iconColor: Theme.AppTheme.textMuted
                }

                MouseArea {
                    id: _closeMA
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.closeRequested()
                }
            }
        }

        // -- Panel body (scrollable) ---------------------------------------
        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: _panelContent.implicitHeight + Theme.AppTheme.marginMd * 2
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: _panelContent
                // `Layout.margins` is a no-op here since this ColumnLayout is
                // a direct child of a Flickable, not of another Layout --
                // real x/y/width insets are needed for the padding to apply.
                x: Theme.AppTheme.marginMd
                y: Theme.AppTheme.marginMd
                width: parent.width - Theme.AppTheme.marginMd * 2
                spacing: Theme.AppTheme.spacingSm

                StatusChip {
                    id: _statusChip
                    visible: root.statusLabel.length > 0
                    status: root.statusLabel
                }

                Repeater {
                    model: root.sections

                    delegate: ColumnLayout {
                        id: sectionDelegate
                        required property var modelData

                        Layout.fillWidth: true
                        spacing: 2
                        visible: String(sectionDelegate.modelData.value || "").length > 0

                        AppControls.Label {
                            text: String(sectionDelegate.modelData.label || "")
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.typeMetadataSize
                            font.bold: true
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(sectionDelegate.modelData.value || "")
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                    }
                }

                ColumnLayout {
                    id: _extraSlot
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.topMargin: 2
                    Layout.preferredHeight: Theme.AppTheme.borderWidthThin
                    color: Theme.AppTheme.divider
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.PrimaryButton {
                        Layout.fillWidth: true
                        visible: root.showEditAction
                        text: root.editActionLabel
                        iconName: "edit"
                        enabled: !root.busy
                        onClicked: root.editRequested()
                    }

                    AppControls.SecondaryButton {
                        visible: root.showSecondaryAction
                        text: root.secondaryActionLabel
                        iconName: "approve"
                        enabled: !root.busy
                        onClicked: root.secondaryActionRequested()
                    }
                }
            }
        }
    }
}
