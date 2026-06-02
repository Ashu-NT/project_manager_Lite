pragma ComponentBehavior: Bound
import App.Controls 1.0 as AppControls

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Dialogs 1.0 as PlatformDialogs
import Platform.Widgets 1.0 as PlatformWidgets
import Shell.Context 1.0 as ShellContexts
import "components" as Components
import "sections" as Sections

AppLayouts.WorkspaceFrame {
    id: root

    // ── Public API (backward-compatible) ─────────────────────────
    property ShellContexts.ShellContext shellModel
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var workspaceModel: root.platformCatalog
        ? root.platformCatalog.workspace("platform.settings")
        : ({ "routeId": "platform.settings", "title": "Settings", "summary": "" })
    property PlatformControllers.PlatformSettingsWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.settingsWorkspace
        : null

    function moduleItemById(itemId) {
        const items = root.workspaceController
            ? (root.workspaceController.moduleEntitlements.items || []) : []
        for (let i = 0; i < items.length; i++) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    title: root.workspaceController
        ? (root.workspaceController.overview.title || root.workspaceModel.title)
        : root.workspaceModel.title
    subtitle: root.workspaceController ? root.workspaceController.overview.subtitle : ""

    // ── Internal state ────────────────────────────────────────────
    property string _activeSection: "modules"
    property string _selectedRowId: ""
    property bool _moduleDetailOpen: false

    readonly property bool _detailOpen: root._moduleDetailOpen
        && root._activeSection === "modules"

    readonly property var _selectedItem: {
        const id = root._selectedRowId
        if (!id) return null
        const items = root.workspaceController
            ? (root.workspaceController.moduleEntitlements.items || []) : []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    readonly property bool   _busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   _load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string _err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string _ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    readonly property int _moduleCount: root.workspaceController
        ? (root.workspaceController.moduleEntitlements.items || []).length : 0
    readonly property int _capCount: root.workspaceController
        ? (root.workspaceController.integrationCapabilities.items || []).length : 0

    readonly property var _moduleContextActions: {
        const item = root._selectedItem
        if (root._activeSection !== "modules" || !item) return []
        return [
            { id: "lifecycle", label: "Lifecycle", icon: "settings", enabled: !!(item.canTertiaryAction), danger: false },
            { id: "licensed",  label: "Licensed",  icon: "approve",  enabled: !!(item.canPrimaryAction),  danger: false },
            { id: "enabled",   label: "Enabled",   icon: "approve",  enabled: !!(item.canSecondaryAction), danger: false }
        ]
    }

    readonly property var _moduleColumns: [
        { key: "title",       label: "Module",          flex: 2, minWidth: 140, sortable: true,  visible: true },
        { key: "subtitle",    label: "Stage / License", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Lifecycle",       flex: 0, minWidth: 100, sortable: false, visible: true, type: "status" },
        { key: "metaText",    label: "Runtime",         flex: 3, minWidth: 200, sortable: false, visible: true }
    ]
    readonly property var _capColumns: [
        { key: "title",       label: "Capability",  flex: 4, minWidth: 220, sortable: true,  visible: true },
        { key: "subtitle",    label: "Provider",    flex: 1, minWidth: 90,  sortable: true,  visible: true },
        { key: "metaText",    label: "Consumers",   flex: 3, minWidth: 140, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",      flex: 0, minWidth: 90,  sortable: false, visible: true, type: "status" }
    ]

    // ── Shell layout ──────────────────────────────────────────────
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ── Left navigation sidebar ───────────────────────────────
        Components.SettingsSidebarNav {
            id: _sidebar
            Layout.fillHeight: true
            Layout.preferredWidth: implicitWidth
            activeSection: root._activeSection
            onSectionChanged: function(section) {
                root._activeSection = section
                root._selectedRowId = ""
                root._moduleDetailOpen = false
            }
        }

        // ── Right side: metrics + banners + content ───────────────
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            AppWidgets.KpiStrip {
                Layout.fillWidth: true
                metrics: root.workspaceController
                    ? (root.workspaceController.overview.metrics || []) : []
            }

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: (root._load || root._busy) && root._err.length === 0
                tone: "info"
                message: root._busy ? "Saving changes..." : "Loading..."
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

            // ── Content area ──────────────────────────────────────
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Sections.SettingsRuntimeSection {
                        anchors.fill: parent
                        visible: root._activeSection === "runtime"
                        clip: true
                        workspaceController: root.workspaceController
                        shellModel: root.shellModel
                        workspaceModel: root.workspaceModel
                        busy: root._busy
                    }

                    Sections.SettingsModulesSection {
                        anchors.fill: parent
                        visible: root._activeSection === "modules" && !root._detailOpen
                        workspaceController: root.workspaceController
                        moduleColumns: root._moduleColumns
                        moduleCount: root._moduleCount
                        selectedRowId: root._selectedRowId
                        busy: root._busy
                        load: root._load
                        onRowSelected: function(id) { root._selectedRowId = id }
                        onRowActivated: function(id) {
                            root._selectedRowId = id
                            root._moduleDetailOpen = true
                        }
                    }

                    Sections.SettingsDefaultsSection {
                        anchors.fill: parent
                        visible: root._activeSection === "defaults"
                    }

                    Sections.SettingsIntegrationsSection {
                        anchors.fill: parent
                        visible: root._activeSection === "integrations"
                        workspaceController: root.workspaceController
                        capColumns: root._capColumns
                        capCount: root._capCount
                        busy: root._busy
                        load: root._load
                    }

                    Sections.SettingsSecuritySection {
                        anchors.fill: parent
                        visible: root._activeSection === "security"
                    }

                    Sections.SettingsSysInfoSection {
                        anchors.fill: parent
                        visible: root._activeSection === "sysinfo"
                        workspaceController: root.workspaceController
                        busy: root._busy
                    }
                }
            }
        }
    }

    // ── Module detail page — full-area overlay ────────────────────
    Loader {
        id: _moduleDetailLoader
        anchors.fill: parent
        z: 10
        active: root._detailOpen
        visible: root._detailOpen && status === Loader.Ready
        asynchronous: true
        sourceComponent: Component {
            SettingsModuleDetailPage {
                module: root._selectedItem || ({})
                lifecycleOptions: root.workspaceController ? (root.workspaceController.lifecycleOptions || []) : []
                busy: root._busy
                errorMessage: root._err
                feedbackMessage: root._ok
                onBackRequested: {
                    root._moduleDetailOpen = false
                    root._selectedRowId = ""
                }
                onLifecycleChangeRequested: function(moduleCode, lifecycleStatus) {
                    if (root.workspaceController)
                        root.workspaceController.changeModuleLifecycleStatus(moduleCode, lifecycleStatus)
                }
                onToggleLicensedRequested: function(moduleCode) {
                    if (root.workspaceController)
                        root.workspaceController.toggleModuleLicensed(moduleCode)
                }
                onToggleEnabledRequested: function(moduleCode) {
                    if (root.workspaceController)
                        root.workspaceController.toggleModuleEnabled(moduleCode)
                }
            }
        }
    }
}
