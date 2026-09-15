pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import tenants.dialogs 1.0 as TenantDialogs

AppLayouts.WorkspaceFrame {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var controller: root.platformCatalog ? root.platformCatalog.tenantSwitcher : null

    readonly property var    _tenants: root.controller ? (root.controller.tenants || []) : []
    readonly property string _activeId: root.controller ? root.controller.activeTenantId : ""
    readonly property bool   _loading: root.controller ? root.controller.isLoading : false
    readonly property bool   _busy:    root.controller ? root.controller.isBusy : false
    readonly property string _err:     root.controller ? root.controller.errorMessage : ""
    readonly property string _ok:      root.controller ? root.controller.feedbackMessage : ""
    readonly property bool   _canCreate: root.platformCatalog
        ? root.platformCatalog.hasPermission("platform.admin")
        : true

    title: "Tenant Management"
    subtitle: root._tenants.length > 0
        ? root._tenants.length + " tenant" + (root._tenants.length === 1 ? "" : "s")
        : ""

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Status messages ───────────────────────────────────────
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: (root._loading || root._busy) && root._err.length === 0
            tone: "info"
            message: root._busy ? "Switching tenant..." : "Loading..."
        }
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root._err.length > 0
            tone: "danger"
            message: root._err
        }
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root._ok.length > 0 && root._err.length === 0
            tone: "success"
            message: root._ok
        }

        // ── Toolbar ───────────────────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: Theme.AppTheme.spacingSm
            Layout.bottomMargin: Theme.AppTheme.spacingSm
            spacing: Theme.AppTheme.spacingSm

            Item { Layout.fillWidth: true }

            AppControls.PrimaryButton {
                text: "New Tenant"
                iconName: "add"
                enabled: !root._loading && !root._busy && root._canCreate
                onClicked: createDialog.openForCreate()
            }

            AppControls.SecondaryButton {
                text: "Refresh"
                iconName: "refresh"
                enabled: !root._loading && !root._busy
                onClicked: { if (root.controller) root.controller.refresh() }
            }
        }

        // ── Tenant list ───────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.AppTheme.surface
            radius: Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.divider
            border.width: 1
            clip: true

            AppControls.Label {
                anchors.centerIn: parent
                visible: root._tenants.length === 0 && !root._loading && root._err.length === 0
                text: "No tenants available"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
            }

            // R6.5: friendlier fallback than the raw danger banner when
            // the underlying data call fails and leaves nothing to show.
            AppWidgets.PermissionState {
                anchors.fill: parent
                visible: root._tenants.length === 0 && !root._loading && root._err.length > 0
                message: root._err
            }

            ScrollView {
                anchors.fill: parent
                contentWidth: availableWidth

                ListView {
                    id: _list
                    model: root._tenants
                    spacing: 0
                    clip: true

                    delegate: Item {
                        id: _row
                        required property var modelData
                        required property int index

                        width: _list.width
                        height: 56

                        readonly property bool _isCurrent: root._activeId === modelData.id
                        readonly property bool _canSwitch: modelData.isActive === true && !_isCurrent

                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 1
                            color: Theme.AppTheme.divider
                            visible: _row.index < root._tenants.length - 1
                        }

                        Rectangle {
                            anchors.fill: parent
                            color: _row._isCurrent
                                ? Theme.AppTheme.accentSoft
                                : (_rowHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent")
                        }

                        HoverHandler { id: _rowHover }

                        RowLayout {
                            anchors {
                                left: parent.left
                                right: parent.right
                                verticalCenter: parent.verticalCenter
                                leftMargin: Theme.AppTheme.marginMd
                                rightMargin: Theme.AppTheme.marginMd
                            }
                            spacing: Theme.AppTheme.spacingMd

                            // Status dot
                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: {
                                    const s = _row.modelData.tenantStatus || ""
                                    if (s === "active")    return Theme.AppTheme.success
                                    if (s === "suspended") return Theme.AppTheme.warning
                                    return Theme.AppTheme.textMuted
                                }
                            }

                            // Name + code
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: _row.modelData.displayName || _row.modelData.tenantCode || ""
                                    color: _row.modelData.isActive
                                        ? Theme.AppTheme.textPrimary
                                        : Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.bold: _row._isCurrent
                                    elide: Text.ElideRight
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: _row.modelData.tenantCode || ""
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    elide: Text.ElideRight
                                }
                            }

                            // Current badge
                            Rectangle {
                                visible: _row._isCurrent
                                radius: Theme.AppTheme.radiusSm
                                color: Theme.AppTheme.accentSoft
                                implicitWidth: _currentLabel.implicitWidth + 12
                                implicitHeight: Theme.AppTheme.inputHeight - 8

                                AppControls.Label {
                                    id: _currentLabel
                                    anchors.centerIn: parent
                                    text: "Current"
                                    color: Theme.AppTheme.accent
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                            }

                            // Status badge (suspended / archived only)
                            Rectangle {
                                visible: !_row.modelData.isActive
                                radius: Theme.AppTheme.radiusSm
                                color: (_row.modelData.tenantStatus === "suspended")
                                    ? Theme.AppTheme.warningSoft
                                    : Theme.AppTheme.dangerSoft
                                implicitWidth: _statusLabel.implicitWidth + 12
                                implicitHeight: Theme.AppTheme.inputHeight - 8

                                AppControls.Label {
                                    id: _statusLabel
                                    anchors.centerIn: parent
                                    text: {
                                        const s = _row.modelData.tenantStatus || ""
                                        return s.length > 0
                                            ? s.charAt(0).toUpperCase() + s.slice(1)
                                            : ""
                                    }
                                    color: (_row.modelData.tenantStatus === "suspended")
                                        ? Theme.AppTheme.warning
                                        : Theme.AppTheme.danger
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                            }

                            // Switch button
                            AppControls.SecondaryButton {
                                text: "Switch"
                                visible: !_row._isCurrent
                                enabled: _row._canSwitch && !root._busy
                                onClicked: {
                                    if (root.controller)
                                        root.controller.switchToTenant(_row.modelData.id)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    TenantDialogs.TenantCreateDialog {
        id: createDialog
        parent: Overlay.overlay
        busy: root._busy

        onSaveRequested: function(payload) {
            if (!root.controller) return
            const result = root.controller.createTenant(payload)
            if (!result || result.ok === false) {
                createDialog.errorMessage = String((result && result.message) || "Operation failed. Please try again.")
            } else {
                createDialog.errorMessage = ""
                createDialog.close()
            }
        }
    }
}
