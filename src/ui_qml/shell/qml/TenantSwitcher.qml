import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Rectangle {
    id: root

    // controller is TenantSwitcherController (PlatformWorkspaceControllerBase)
    property var controller: null
    property var platformCatalog: null

    readonly property string _activeName: {
        if (!root.controller) return ""
        const active = root.controller.activeTenantId
        const list = root.controller.tenants || []
        for (let i = 0; i < list.length; i++) {
            if (list[i].id === active) return String(list[i].displayName || list[i].tenantCode || "")
        }
        return ""
    }

    visible: root.controller ? root.controller.isMultiTenant : false
    implicitWidth: visible ? (tenantRow.implicitWidth + Theme.AppTheme.spacingMd) : 0
    implicitHeight: Theme.AppTheme.inputHeight
    radius: Theme.AppTheme.radiusSm
    color: switchHover.containsMouse ? Theme.AppTheme.hoverSurface : Theme.AppTheme.surfaceOverlay

    Connections {
        target: root.controller
        function onTenantSwitched() {
            if (root.platformCatalog && typeof root.platformCatalog.refreshAllWorkspaces === "function") {
                root.platformCatalog.refreshAllWorkspaces()
            }
        }
    }

    RowLayout {
        id: tenantRow
        anchors.centerIn: parent
        spacing: Theme.AppTheme.spacingXs

        AppIcons.AppIcon {
            name: "tenant"
            size: Theme.AppTheme.iconSm
            iconColor: Theme.AppTheme.textMuted
        }

        AppControls.Label {
            text: root._activeName
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold: true
            elide: Text.ElideRight
            maximumLineCount: 1
        }

        AppIcons.AppIcon {
            name: "chevron_down"
            size: Theme.AppTheme.iconSm
            iconColor: Theme.AppTheme.textMuted
        }
    }

    MouseArea {
        id: switchHover
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: tenantMenu.open()
    }

    Menu {
        id: tenantMenu
        y: root.height + 4

        Repeater {
            model: root.controller ? (root.controller.tenants || []) : []
            delegate: MenuItem {
                required property var modelData
                readonly property bool _isCurrent: root.controller
                    ? (root.controller.activeTenantId === modelData.id)
                    : false
                readonly property bool _canSwitch: modelData.isActive === true

                text: modelData.displayName || modelData.tenantCode || ""
                enabled: _canSwitch && !_isCurrent
                checkable: true
                checked: _isCurrent

                contentItem: RowLayout {
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: modelData.displayName || modelData.tenantCode || ""
                        color: (_canSwitch && !_isCurrent)
                            ? Theme.AppTheme.textPrimary
                            : Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: _isCurrent
                        elide: Text.ElideRight
                    }

                    AppControls.Label {
                        visible: !modelData.isActive
                        text: String(modelData.tenantStatus || "")
                        color: modelData.tenantStatus === "suspended"
                            ? Theme.AppTheme.warning
                            : Theme.AppTheme.danger
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                    }
                }

                onTriggered: {
                    if (!_canSwitch || _isCurrent) return
                    root.controller.switchToTenant(modelData.id)
                }
            }
        }
    }

    ToolTip {
        visible: switchHover.containsMouse && (root.controller ? root.controller.isMultiTenant : false)
        text: "Switch tenant"
        delay: 400
    }
}
