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

    property string statusTone: ""
    property bool showHeader: true

    // -- Metadata sections ------------------------------------------------
    // Array of { label, value } sections rendered below the header, in
    // order. Entries with an empty value are hidden automatically. Ignored
    // once `groups` (below) is non-empty.
    property var sections: []

    // -- Grouped metadata (opt-in) -----------------------------------------
    // Array of { title, rows: [{label, value}] } -- an enterprise-style
    // grouped layout (e.g. Identity / Lifecycle / Location / Key
    // Statistics / Business Context) rendered instead of the flat
    // `sections` list above. A group with every row empty is hidden
    // entirely, same as an individual empty row in the flat list. Existing
    // consumers that only set `sections` are completely unaffected.
    property var groups: []

    // -- Actions ----------------------------------------------------------
    property bool busy: false
    property string editActionLabel: "Edit"
    property bool showEditAction: true
    property string secondaryActionLabel: ""
    property bool showSecondaryAction: false
    // A distinct third action -- e.g. "View Details" to open the record's
    // full detail page. Generic, not organization-specific: any consumer
    // that has a real detail page destination may opt in. Rendered as its
    // own full-width row below Edit/Secondary by default; set
    // `viewDetailsPrimary` to promote it to the top, primary action
    // instead (an enterprise "[Open Details] / [Edit] [Actions ▾]"
    // hierarchy) -- opt-in, existing consumers are unaffected.
    property string viewDetailsLabel: "View Details"
    property bool showViewDetailsAction: false
    property bool viewDetailsPrimary: false

    // -- Actions overflow menu (opt-in) -------------------------------------
    // Renders an "Actions ▾" button next to Edit using the same
    // {id,label,icon,danger,enabled,separator} item shape as
    // ActionsMenuButton elsewhere (see SectionDetailPage.menuActions) --
    // for a record with more than one quick lifecycle action. Independent
    // of (and rendered alongside) the single-action `showSecondaryAction`
    // mechanism above, which still works unchanged for existing consumers.
    property var menuActions: []
    property string menuTriggerLabel: "Actions"

    // -- Extra content slot (e.g. a document preview, entity-specific
    // panel) rendered between the metadata sections and the action row.
    default property alias extraContent: _extraSlot.data

    signal closeRequested()
    signal editRequested()
    signal secondaryActionRequested()
    signal viewDetailsRequested()
    signal menuActionTriggered(string id)

    color: Theme.AppTheme.surface
    property int panelWidth: Theme.AppTheme.inspectorWidth
    implicitWidth: root.panelWidth

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
                    tone:   root.statusTone
                }

                Repeater {
                    model: root.groups.length > 0 ? [] : root.sections

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

                // -- Grouped metadata (opt-in, see `groups` above) -----------
                Repeater {
                    model: root.groups

                    delegate: ColumnLayout {
                        id: groupDelegate
                        required property var modelData

                        readonly property var _rows: groupDelegate.modelData.rows || []
                        readonly property bool _hasContent: {
                            for (let i = 0; i < groupDelegate._rows.length; i += 1) {
                                if (String(groupDelegate._rows[i].value || "").length > 0) return true
                            }
                            return false
                        }

                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs
                        visible: groupDelegate._hasContent

                        AppControls.Label {
                            text: String(groupDelegate.modelData.title || "")
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.sectionTitleSize
                            font.bold: true
                            font.letterSpacing: 0.6
                        }

                        Repeater {
                            model: groupDelegate._rows

                            delegate: ColumnLayout {
                                id: rowDelegate
                                required property var modelData

                                Layout.fillWidth: true
                                spacing: 2
                                visible: String(rowDelegate.modelData.value || "").length > 0

                                AppControls.Label {
                                    text: String(rowDelegate.modelData.label || "")
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.typeMetadataSize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(rowDelegate.modelData.value || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
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

                // Enterprise hierarchy (opt-in via viewDetailsPrimary): a
                // full-width primary "[Open Details]" button on top, with
                // "[Edit]" and an "[Actions ▾]" overflow menu sharing a
                // secondary row below. Default (viewDetailsPrimary=false)
                // keeps every existing consumer's layout unchanged --
                // Edit as the primary button, View Details as its own
                // full-width secondary row underneath.
                AppControls.PrimaryButton {
                    Layout.fillWidth: true
                    visible: root.showViewDetailsAction && root.viewDetailsPrimary
                    text: root.viewDetailsLabel
                    iconName: "chevron_right"
                    enabled: !root.busy
                    onClicked: root.viewDetailsRequested()
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.PrimaryButton {
                        Layout.fillWidth: true
                        visible: root.showEditAction && !root.viewDetailsPrimary
                        text: root.editActionLabel
                        iconName: "edit"
                        enabled: !root.busy
                        onClicked: root.editRequested()
                    }

                    AppControls.SecondaryButton {
                        Layout.fillWidth: true
                        visible: root.showEditAction && root.viewDetailsPrimary
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

                    ActionsMenuButton {
                        visible: root.menuActions.length > 0
                        enabled: !root.busy
                        items: root.menuActions
                        triggerLabel: root.menuTriggerLabel
                        onActionSelected: function(id) { root.menuActionTriggered(id) }
                    }
                }

                AppControls.SecondaryButton {
                    Layout.fillWidth: true
                    visible: root.showViewDetailsAction && !root.viewDetailsPrimary
                    text: root.viewDetailsLabel
                    iconName: "chevron_right"
                    enabled: !root.busy
                    onClicked: root.viewDetailsRequested()
                }
            }
        }
    }
}
