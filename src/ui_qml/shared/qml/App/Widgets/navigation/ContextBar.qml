pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls


Rectangle {
    id: root

    // Tenant half -- caller hides this entirely when not multi-tenant,
    // mirroring TenantSwitcher.qml's existing isMultiTenant gating today.
    property bool tenantSwitcherVisible: true
    property string tenantName: ""
    property var tenantOptions: [] // [{ id, label }]

    // Organization half -- always visible; per §5 this is the gap being closed.
    property string organizationName: ""
    property var organizationOptions: [] // [{ id, label }]

    signal tenantSelected(string tenantId)
    signal organizationSelected(string organizationId)
    signal manageTenantsRequested()
    signal manageOrganizationsRequested()

    implicitHeight: Theme.AppTheme.toolbarHeight
    color: Theme.AppTheme.surfaceAlt

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingMd

        ContextChip {
            id: _tenantChip
            objectName: "contextBarTenantChip"
            visible: root.tenantSwitcherVisible
            label: "Tenant"
            value: root.tenantName
            options: root.tenantOptions
            manageLabel: "Manage tenants…"
            onOptionSelected: function(id) { root.tenantSelected(id) }
            onManageRequested: root.manageTenantsRequested()
        }

        ContextChip {
            id: _organizationChip
            objectName: "contextBarOrganizationChip"
            label: "Organization"
            value: root.organizationName
            options: root.organizationOptions
            manageLabel: "Manage organizations…"
            onOptionSelected: function(id) { root.organizationSelected(id) }
            onManageRequested: root.manageOrganizationsRequested()
        }

        Item { Layout.fillWidth: true }
    }

    component ContextChip: Item {
        id: chip

        property string label: ""
        property string value: ""
        property var options: []
        property string manageLabel: ""

        signal optionSelected(string id)
        signal manageRequested()

        Layout.preferredWidth: _row.implicitWidth
        Layout.fillHeight: true

        activeFocusOnTab: true
        Accessible.role: Accessible.Button
        Accessible.name: chip.label + ": " + (chip.value.length > 0 ? chip.value : "none selected")
        Accessible.onPressAction: _popup.open()
        Keys.onPressed: (event) => {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                _popup.open()
                event.accepted = true
            }
        }

        Rectangle {
            anchors.fill: _row
            anchors.margins: -4
            radius: Theme.AppTheme.radiusSm
            color: "transparent"
            border.width: chip.activeFocus ? 2 : 0
            border.color: Theme.AppTheme.focusBorder
        }

        RowLayout {
            id: _row
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label {
                text: chip.label + ":"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.typeSupportingTextSize
            }

            AppControls.Label {
                text: chip.value.length > 0 ? chip.value : "—"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                font.bold: true
            }

            AppIcons.AppIcon {
                name: "chevron_down"
                size: Theme.AppTheme.iconXs
                iconColor: Theme.AppTheme.textMuted
            }
        }

        MouseArea {
            anchors.fill: _row
            cursorShape: Qt.PointingHandCursor
            onClicked: _popup.open()
        }

        AnchoredPopup {
            id: _popup
            anchorItem: chip
            placement: "below-left"
            width: 240

            contentItem: ColumnLayout {
                spacing: Theme.AppTheme.spacingXs

                Repeater {
                    model: chip.options

                    delegate: Item {
                        id: optionDelegate
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: Theme.AppTheme.sidebarRowHeight

                        activeFocusOnTab: true
                        Accessible.role: Accessible.MenuItem
                        Accessible.name: String(optionDelegate.modelData.label || "")
                        Accessible.onPressAction: {
                            chip.optionSelected(String(optionDelegate.modelData.id || ""))
                            _popup.close()
                        }
                        Keys.onPressed: (event) => {
                            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                                chip.optionSelected(String(optionDelegate.modelData.id || ""))
                                _popup.close()
                                event.accepted = true
                            }
                        }

                        Rectangle {
                            anchors.fill: parent
                            visible: optionDelegate.activeFocus
                            color: Theme.AppTheme.hoverSurface
                            border.width: 2
                            border.color: Theme.AppTheme.focusBorder
                        }

                        AppControls.Label {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: Theme.AppTheme.spacingSm
                            text: String(optionDelegate.modelData.label || "")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                chip.optionSelected(String(optionDelegate.modelData.id || ""))
                                _popup.close()
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: Theme.AppTheme.borderWidthThin
                    color: Theme.AppTheme.divider
                }

                Item {
                    Layout.fillWidth: true
                    implicitHeight: Theme.AppTheme.sidebarRowHeight

                    activeFocusOnTab: true
                    Accessible.role: Accessible.MenuItem
                    Accessible.name: chip.manageLabel
                    Accessible.onPressAction: {
                        chip.manageRequested()
                        _popup.close()
                    }
                    Keys.onPressed: (event) => {
                        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                            chip.manageRequested()
                            _popup.close()
                            event.accepted = true
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        visible: parent.activeFocus
                        color: Theme.AppTheme.hoverSurface
                        border.width: 2
                        border.color: Theme.AppTheme.focusBorder
                    }

                    AppControls.Label {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.AppTheme.spacingSm
                        text: chip.manageLabel
                        color: Theme.AppTheme.accent
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            chip.manageRequested()
                            _popup.close()
                        }
                    }
                }
            }
        }
    }
}
