import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Dialogs 1.0 as PlatformDialogs
import Platform.Widgets 1.0 as PlatformWidgets
import Shell.Context 1.0 as ShellContexts

AppLayouts.WorkspaceFrame {
    id: root

    // ── Public API (backward-compatible) ─────────────────────────
    property ShellContexts.ShellContext shellModel
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var workspaceModel: root.platformCatalog
        ? root.platformCatalog.workspace("platform.settings")
        : ({
            "routeId": "platform.settings",
            "title": "Settings",
            "summary": ""
        })
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

    title:    root.workspaceController
        ? (root.workspaceController.overview.title || root.workspaceModel.title)
        : root.workspaceModel.title
    subtitle: root.workspaceController ? root.workspaceController.overview.subtitle : ""

    // ── Internal state ────────────────────────────────────────────
    property string _activeSection: "modules"
    property string _selectedRowId: ""

    readonly property bool _detailOpen: root._selectedRowId.length > 0
        && (root._activeSection === "modules" || root._activeSection === "profiles")

    readonly property var _selectedItem: {
        const id = root._selectedRowId
        if (!id) return null
        const s = root._activeSection
        let items = []
        if      (s === "modules")  items = root.workspaceController ? (root.workspaceController.moduleEntitlements.items   || []) : []
        else if (s === "profiles") items = root.workspaceController ? (root.workspaceController.organizationProfiles.items || []) : []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }

    readonly property bool   _busy: root.workspaceController ? root.workspaceController.isBusy          : false
    readonly property bool   _load: root.workspaceController ? root.workspaceController.isLoading       : false
    readonly property string _err:  root.workspaceController ? root.workspaceController.errorMessage    : ""
    readonly property string _ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    readonly property int _moduleCount:  root.workspaceController
        ? (root.workspaceController.moduleEntitlements.items   || []).length : 0
    readonly property int _profileCount: root.workspaceController
        ? (root.workspaceController.organizationProfiles.items || []).length : 0

    readonly property var _moduleContextActions: {
        const item = root._selectedItem
        if (root._activeSection !== "modules" || !item) return []
        return [
            { id: "lifecycle", label: "Lifecycle", icon: "settings", enabled: !!(item.canTertiaryAction), danger: false },
            { id: "licensed",  label: "Licensed",  icon: "approve",  enabled: !!(item.canPrimaryAction),  danger: false },
            { id: "enabled",   label: "Enabled",   icon: "approve",  enabled: !!(item.canSecondaryAction), danger: false }
        ]
    }

    // ── Column definitions ────────────────────────────────────────
    readonly property var _moduleColumns: [
        { key: "title",       label: "Module",          flex: 2, minWidth: 140, sortable: true,  visible: true },
        { key: "subtitle",    label: "Stage / License", flex: 3, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Lifecycle",       flex: 0, minWidth: 100, sortable: false, visible: true,
          type: "status" },
        { key: "metaText",    label: "Runtime",         flex: 3, minWidth: 200, sortable: false, visible: true }
    ]

    readonly property var _profileColumns: [
        { key: "title",       label: "Name",    flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Details", flex: 3, minWidth: 120, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",  flex: 0, minWidth: 90,  sortable: false, visible: true,
          type: "status" },
        { key: "metaText",    label: "Info",    flex: 2, minWidth: 120, sortable: false, visible: true }
    ]

    // ── Shell layout ──────────────────────────────────────────────
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ── Left navigation sidebar ───────────────────────────────
        Item {
            id: _sidebar
            property bool collapsed: false

            Layout.fillHeight:    true
            Layout.preferredWidth: implicitWidth

            implicitWidth: _sidebar.collapsed ? 48 : 220

            Behavior on implicitWidth {
                NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
            }

            Rectangle {
                anchors.fill: parent
                color: Theme.AppTheme.navBackground

                Rectangle {
                    anchors { top: parent.top; bottom: parent.bottom; right: parent.right }
                    width: 1; color: Theme.AppTheme.divider
                }
            }

            // Header
            Item {
                id: _sidebarHead
                anchors.top:   parent.top
                anchors.left:  parent.left
                anchors.right: parent.right
                height: 40

                Label {
                    visible:                !_sidebar.collapsed
                    anchors.left:           parent.left
                    anchors.leftMargin:     14
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right:          _sidebarToggle.left
                    anchors.rightMargin:    4
                    text:           "Settings"
                    color:          Theme.AppTheme.textPrimary
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold:      true
                    elide:          Text.ElideRight
                }

                Rectangle {
                    id: _sidebarToggle
                    anchors.right:          parent.right
                    anchors.rightMargin:    6
                    anchors.verticalCenter: parent.verticalCenter
                    width: 28; height: 28; radius: 4
                    color: _toggleMA.containsMouse
                        ? Theme.AppTheme.navHoverBackground : "transparent"

                    AppIcons.AppIcon {
                        anchors.centerIn: parent
                        name:      _sidebar.collapsed ? "chevron_right" : "chevron_left"
                        size:      11
                        iconColor: Theme.AppTheme.textMuted
                    }

                    MouseArea {
                        id: _toggleMA
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape:  Qt.PointingHandCursor
                        onClicked:    _sidebar.collapsed = !_sidebar.collapsed
                    }
                }

                Rectangle {
                    anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                    height: 1; color: Theme.AppTheme.divider
                }
            }

            // Nav list
            ListView {
                anchors.top:    _sidebarHead.bottom
                anchors.left:   parent.left
                anchors.right:  parent.right
                anchors.bottom: parent.bottom
                clip:           true
                topMargin:      4
                bottomMargin:   4
                boundsBehavior: Flickable.StopAtBounds

                model: [
                    { type: "group", label: "PLATFORM"                                                           },
                    { type: "item",  section: "runtime",      label: "Runtime",               icon: "settings"  },
                    { type: "item",  section: "modules",      label: "Module Entitlements",   icon: "project"   },
                    { type: "item",  section: "profiles",     label: "Org Profiles",          icon: "admin"     },
                    { type: "group", label: "CONFIGURATION"                                                      },
                    { type: "item",  section: "defaults",     label: "Platform Defaults",     icon: "register"  },
                    { type: "item",  section: "integrations", label: "Integrations",          icon: "collaboration" },
                    { type: "item",  section: "security",     label: "Security",              icon: "control"   },
                    { type: "group", label: "SYSTEM"                                                             },
                    { type: "item",  section: "sysinfo",      label: "System Info",           icon: "history"   }
                ]

                delegate: Item {
                    property var  _d:       modelData
                    property bool _isGroup: _d.type === "group"
                    property bool _isItem:  _d.type === "item"

                    width:   ListView.view.width
                    height:  _isGroup ? (_sidebar.collapsed ? 0 : 24) : 34
                    visible: _isGroup ? !_sidebar.collapsed : true
                    clip:    true

                    Label {
                        visible:            _isGroup
                        anchors.left:       parent.left
                        anchors.leftMargin: 14
                        anchors.bottom:     parent.bottom
                        anchors.bottomMargin: 3
                        text:           _d.label || ""
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold:      true
                        font.letterSpacing: 0.7
                    }

                    Rectangle {
                        id: _navBg
                        visible:             _isItem
                        anchors.fill:        parent
                        anchors.leftMargin:  4
                        anchors.rightMargin: 4
                        radius: 4

                        readonly property bool _active: root._activeSection === (_d.section || "")

                        color: _active
                            ? Theme.AppTheme.navSelectedBackground
                            : _navMA.containsMouse
                                ? Theme.AppTheme.navHoverBackground : "transparent"

                        Rectangle {
                            visible: _navBg._active
                            anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                            anchors.topMargin: 5; anchors.bottomMargin: 5
                            width: 3; radius: 2
                            color: Theme.AppTheme.accent
                        }

                        AppIcons.AppIcon {
                            id: _navIco
                            anchors.left:           parent.left
                            anchors.leftMargin:     _sidebar.collapsed ? 13 : 11
                            anchors.verticalCenter: parent.verticalCenter
                            name:      _d.icon || "settings"
                            size:      13
                            iconColor: _navBg._active
                                ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                        }

                        Label {
                            visible:                !_sidebar.collapsed
                            anchors.left:           _navIco.right
                            anchors.leftMargin:     9
                            anchors.right:          parent.right
                            anchors.rightMargin:    8
                            anchors.verticalCenter: parent.verticalCenter
                            text:           _d.label || ""
                            color:          _navBg._active
                                ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold:      _navBg._active
                            elide:          Text.ElideRight
                        }

                        ToolTip.visible: _sidebar.collapsed && _navMA.containsMouse
                        ToolTip.text:    _d.label || ""
                        ToolTip.delay:   700

                        MouseArea {
                            id: _navMA
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape:  Qt.PointingHandCursor
                            onClicked: {
                                const s = _d.section || ""
                                if (s.length > 0) {
                                    root._activeSection = s
                                    root._selectedRowId = ""
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── Right side: metrics + banners + content ───────────────
        ColumnLayout {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            spacing: 0

            // ── Compact metrics strip ─────────────────────────────
            AppWidgets.KpiStrip {
                Layout.fillWidth: true
                metrics: root.workspaceController
                    ? (root.workspaceController.overview.metrics || []) : []
            }

            // ── Inline state banners ──────────────────────────────
            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: (root._load || root._busy) && root._err.length === 0
                tone:    "info"
                message: root._busy ? "Saving changes..." : "Loading..."
            }
            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: root._err.length > 0
                tone:    "danger"
                message: root._err
            }
            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: root._ok.length > 0 && root._err.length === 0
                tone:    "success"
                message: root._ok
            }

            // ── Content area: active section + detail panel ───────
            RowLayout {
                Layout.fillWidth:  true
                Layout.fillHeight: true
                spacing: 0

                // ── Section content ───────────────────────────────
                Item {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true

                    // ── Runtime ───────────────────────────────────
                    Item {
                        anchors.fill: parent
                        visible:      root._activeSection === "runtime"
                        clip:         true

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            Rectangle {
                                Layout.fillWidth: true
                                height: Theme.AppTheme.toolbarHeight - 6
                                color:  Theme.AppTheme.surfaceRaised
                                z:      1

                                Rectangle {
                                    anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                    height: 1; color: Theme.AppTheme.divider
                                }

                                RowLayout {
                                    anchors.fill:        parent
                                    anchors.leftMargin:  Theme.AppTheme.marginMd
                                    anchors.rightMargin: 8
                                    spacing:             Theme.AppTheme.spacingXs

                                    Label {
                                        text:           "Runtime Configuration"
                                        color:          Theme.AppTheme.textPrimary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold:      true
                                    }
                                    Item { Layout.fillWidth: true }
                                    Rectangle {
                                        width: 26; height: 26; radius: 4
                                        color: _rtRefreshMA.containsMouse
                                            ? Theme.AppTheme.hoverSurface : "transparent"
                                        AppIcons.AppIcon {
                                            anchors.centerIn: parent
                                            name: "refresh"; size: 12
                                            iconColor: Theme.AppTheme.textMuted
                                        }
                                        MouseArea {
                                            id: _rtRefreshMA
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape:  Qt.PointingHandCursor
                                            enabled:      !root._busy
                                            onClicked: {
                                                if (root.workspaceController)
                                                    root.workspaceController.refresh()
                                            }
                                        }
                                    }
                                }
                            }

                            Flickable {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                contentWidth:      width
                                contentHeight:     _runtimeCol.implicitHeight
                                clip:              true
                                boundsBehavior:    Flickable.StopAtBounds

                                ColumnLayout {
                                    id: _runtimeCol
                                    width:   parent.width
                                    spacing: 0

                                    // ── Property row: Theme Mode ──
                                    Rectangle {
                                        width:  _runtimeCol.width
                                        height: 38
                                        color:  "transparent"
                                        Rectangle {
                                            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                            height: 1; color: Theme.AppTheme.divider
                                        }
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: Theme.AppTheme.marginMd
                                            anchors.rightMargin: Theme.AppTheme.marginMd
                                            spacing: Theme.AppTheme.spacingMd
                                            Label {
                                                Layout.preferredWidth: 120
                                                text: "Theme Mode"
                                                color: Theme.AppTheme.textMuted
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                font.bold: true
                                            }
                                            Label {
                                                Layout.fillWidth: true
                                                text: root.shellModel ? root.shellModel.themeMode : "—"
                                                color: Theme.AppTheme.textPrimary
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }

                                    // ── Property row: Platform API ──
                                    Rectangle {
                                        width:  _runtimeCol.width
                                        height: 38
                                        color:  Theme.AppTheme.surfaceOverlay
                                        Rectangle {
                                            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                            height: 1; color: Theme.AppTheme.divider
                                        }
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: Theme.AppTheme.marginMd
                                            anchors.rightMargin: Theme.AppTheme.marginMd
                                            spacing: Theme.AppTheme.spacingMd
                                            Label {
                                                Layout.preferredWidth: 120
                                                text: "Platform API"
                                                color: Theme.AppTheme.textMuted
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                font.bold: true
                                            }
                                            Label {
                                                Layout.fillWidth: true
                                                text: root.workspaceController
                                                    ? (root.workspaceController.overview.statusLabel || "—") : "—"
                                                color: Theme.AppTheme.textPrimary
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }

                                    // ── Property row: Summary ──
                                    Rectangle {
                                        width:  _runtimeCol.width
                                        height: 38
                                        color:  "transparent"
                                        Rectangle {
                                            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                            height: 1; color: Theme.AppTheme.divider
                                        }
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: Theme.AppTheme.marginMd
                                            anchors.rightMargin: Theme.AppTheme.marginMd
                                            spacing: Theme.AppTheme.spacingMd
                                            Label {
                                                Layout.preferredWidth: 120
                                                text: "Summary"
                                                color: Theme.AppTheme.textMuted
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                font.bold: true
                                            }
                                            Label {
                                                Layout.fillWidth: true
                                                text: root.workspaceModel.summary || "—"
                                                color: Theme.AppTheme.textPrimary
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // ── Module Entitlements ───────────────────────
                    Item {
                        anchors.fill: parent
                        visible:      root._activeSection === "modules"

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            Rectangle {
                                Layout.fillWidth: true
                                height: Theme.AppTheme.toolbarHeight - 6
                                color:  Theme.AppTheme.surfaceRaised
                                z:      1

                                Rectangle {
                                    anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                    height: 1; color: Theme.AppTheme.divider
                                }

                                RowLayout {
                                    anchors.fill:        parent
                                    anchors.leftMargin:  Theme.AppTheme.marginMd
                                    anchors.rightMargin: 8
                                    spacing:             Theme.AppTheme.spacingXs

                                    Label {
                                        text:           "Module Entitlements"
                                        color:          Theme.AppTheme.textPrimary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold:      true
                                    }
                                    Label {
                                        visible:        root._moduleCount > 0
                                        text:           String(root._moduleCount)
                                        color:          Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        leftPadding:    4
                                    }

                                    Item { Layout.fillWidth: true }

                                    Rectangle {
                                        width: 26; height: 26; radius: 4
                                        color: _modRefreshMA.containsMouse
                                            ? Theme.AppTheme.hoverSurface : "transparent"
                                        AppIcons.AppIcon {
                                            anchors.centerIn: parent
                                            name: "refresh"; size: 12
                                            iconColor: Theme.AppTheme.textMuted
                                        }
                                        MouseArea {
                                            id: _modRefreshMA
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape:  Qt.PointingHandCursor
                                            enabled:      !root._busy
                                            onClicked: {
                                                if (root.workspaceController)
                                                    root.workspaceController.refresh()
                                            }
                                        }
                                    }
                                }
                            }

                            // Contextual module actions — visible when a module is selected
                            AppWidgets.ContextualActionToolbar {
                                Layout.fillWidth: true
                                visible:  root._activeSection === "modules"
                                    && root._selectedRowId.length > 0
                                title:    root._selectedItem ? (root._selectedItem.title || "") : ""
                                subtitle: root._selectedItem ? (root._selectedItem.statusLabel || "") : ""
                                busy:     root._busy
                                actions:  root._moduleContextActions
                                onActionTriggered: function(id) {
                                    if (id === "lifecycle") {
                                        if (root._selectedItem && root.workspaceController)
                                            lifecycleDialog.openForItem(
                                                root._selectedItem,
                                                root.workspaceController.lifecycleOptions || []
                                            )
                                    } else if (id === "licensed") {
                                        if (root.workspaceController)
                                            root.workspaceController.toggleModuleLicensed(root._selectedRowId)
                                    } else if (id === "enabled") {
                                        if (root.workspaceController)
                                            root.workspaceController.toggleModuleEnabled(root._selectedRowId)
                                    }
                                }
                            }

                            AppWidgets.DataTable {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                rows:          root.workspaceController
                                    ? (root.workspaceController.moduleEntitlements.items || []) : []
                                columns:       root._moduleColumns
                                selectedRowId: root._selectedRowId
                                emptyText:     root.workspaceController
                                    ? (root.workspaceController.moduleEntitlements.emptyState || "No modules configured")
                                    : "No modules configured"
                                loading: root._load

                                onRowSelected: function(id) {
                                    root._selectedRowId = id
                                }
                                onRowActivated: function(id) {
                                    root._selectedRowId = id
                                    const item = root.moduleItemById(id)
                                    if (item !== null && root.workspaceController !== null)
                                        lifecycleDialog.openForItem(
                                            item,
                                            root.workspaceController.lifecycleOptions || []
                                        )
                                }
                            }
                        }
                    }

                    // ── Organization Profiles ─────────────────────
                    Item {
                        anchors.fill: parent
                        visible:      root._activeSection === "profiles"

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            Rectangle {
                                Layout.fillWidth: true
                                height: Theme.AppTheme.toolbarHeight - 6
                                color:  Theme.AppTheme.surfaceRaised
                                z:      1

                                Rectangle {
                                    anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                    height: 1; color: Theme.AppTheme.divider
                                }

                                RowLayout {
                                    anchors.fill:        parent
                                    anchors.leftMargin:  Theme.AppTheme.marginMd
                                    anchors.rightMargin: 8
                                    spacing:             Theme.AppTheme.spacingXs

                                    Label {
                                        text:           "Organization Profiles"
                                        color:          Theme.AppTheme.textPrimary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold:      true
                                    }
                                    Label {
                                        visible:        root._profileCount > 0
                                        text:           String(root._profileCount)
                                        color:          Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        leftPadding:    4
                                    }

                                    Item { Layout.fillWidth: true }

                                    Rectangle {
                                        width: 26; height: 26; radius: 4
                                        color: _profRefreshMA.containsMouse
                                            ? Theme.AppTheme.hoverSurface : "transparent"
                                        AppIcons.AppIcon {
                                            anchors.centerIn: parent
                                            name: "refresh"; size: 12
                                            iconColor: Theme.AppTheme.textMuted
                                        }
                                        MouseArea {
                                            id: _profRefreshMA
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape:  Qt.PointingHandCursor
                                            enabled:      !root._busy
                                            onClicked: {
                                                if (root.workspaceController)
                                                    root.workspaceController.refresh()
                                            }
                                        }
                                    }
                                }
                            }

                            AppWidgets.DataTable {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                rows:          root.workspaceController
                                    ? (root.workspaceController.organizationProfiles.items || []) : []
                                columns:       root._profileColumns
                                selectedRowId: root._selectedRowId
                                emptyText:     root.workspaceController
                                    ? (root.workspaceController.organizationProfiles.emptyState || "No profiles configured")
                                    : "No profiles configured"
                                loading: root._load

                                onRowSelected: function(id) { root._selectedRowId = id }
                                onRowActivated: function(id) { root._selectedRowId = id }
                            }
                        }
                    }

                    // ── Platform Defaults (placeholder) ───────────
                    Item {
                        anchors.fill: parent
                        visible:      root._activeSection === "defaults"

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            Rectangle {
                                Layout.fillWidth: true
                                height: Theme.AppTheme.toolbarHeight - 6
                                color:  Theme.AppTheme.surfaceRaised
                                z:      1
                                Rectangle {
                                    anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                    height: 1; color: Theme.AppTheme.divider
                                }
                                Label {
                                    anchors.left:           parent.left
                                    anchors.leftMargin:     Theme.AppTheme.marginMd
                                    anchors.verticalCenter: parent.verticalCenter
                                    text:           "Platform Defaults"
                                    color:          Theme.AppTheme.textPrimary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold:      true
                                }
                            }

                            Item {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                AppWidgets.EmptyState {
                                    anchors.centerIn: parent
                                    width:   Math.min(parent.width, 320)
                                    title:   "Platform Defaults"
                                }
                            }
                        }
                    }

                    // ── Integrations (placeholder) ────────────────
                    Item {
                        anchors.fill: parent
                        visible:      root._activeSection === "integrations"

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            Rectangle {
                                Layout.fillWidth: true
                                height: Theme.AppTheme.toolbarHeight - 6
                                color:  Theme.AppTheme.surfaceRaised
                                z:      1
                                Rectangle {
                                    anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                    height: 1; color: Theme.AppTheme.divider
                                }
                                Label {
                                    anchors.left:           parent.left
                                    anchors.leftMargin:     Theme.AppTheme.marginMd
                                    anchors.verticalCenter: parent.verticalCenter
                                    text:           "Integrations"
                                    color:          Theme.AppTheme.textPrimary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold:      true
                                }
                            }

                            Item {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                AppWidgets.EmptyState {
                                    anchors.centerIn: parent
                                    width:   Math.min(parent.width, 320)
                                    title:   "No integrations configured"
                                }
                            }
                        }
                    }

                    // ── Security (placeholder) ────────────────────
                    Item {
                        anchors.fill: parent
                        visible:      root._activeSection === "security"

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            Rectangle {
                                Layout.fillWidth: true
                                height: Theme.AppTheme.toolbarHeight - 6
                                color:  Theme.AppTheme.surfaceRaised
                                z:      1
                                Rectangle {
                                    anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                    height: 1; color: Theme.AppTheme.divider
                                }
                                Label {
                                    anchors.left:           parent.left
                                    anchors.leftMargin:     Theme.AppTheme.marginMd
                                    anchors.verticalCenter: parent.verticalCenter
                                    text:           "Security"
                                    color:          Theme.AppTheme.textPrimary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold:      true
                                }
                            }

                            Item {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                AppWidgets.EmptyState {
                                    anchors.centerIn: parent
                                    width:   Math.min(parent.width, 320)
                                    title:   "Security configuration"
                                }
                            }
                        }
                    }

                    // ── System Info ───────────────────────────────
                    Item {
                        anchors.fill: parent
                        visible:      root._activeSection === "sysinfo"

                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 0

                            Rectangle {
                                Layout.fillWidth: true
                                height: Theme.AppTheme.toolbarHeight - 6
                                color:  Theme.AppTheme.surfaceRaised
                                z:      1

                                Rectangle {
                                    anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                    height: 1; color: Theme.AppTheme.divider
                                }

                                RowLayout {
                                    anchors.fill:        parent
                                    anchors.leftMargin:  Theme.AppTheme.marginMd
                                    anchors.rightMargin: 8
                                    spacing:             Theme.AppTheme.spacingXs

                                    Label {
                                        text:           "System Info"
                                        color:          Theme.AppTheme.textPrimary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold:      true
                                    }
                                    Item { Layout.fillWidth: true }
                                    Rectangle {
                                        width: 26; height: 26; radius: 4
                                        color: _siRefreshMA.containsMouse
                                            ? Theme.AppTheme.hoverSurface : "transparent"
                                        AppIcons.AppIcon {
                                            anchors.centerIn: parent
                                            name: "refresh"; size: 12
                                            iconColor: Theme.AppTheme.textMuted
                                        }
                                        MouseArea {
                                            id: _siRefreshMA
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape:  Qt.PointingHandCursor
                                            enabled:      !root._busy
                                            onClicked: {
                                                if (root.workspaceController)
                                                    root.workspaceController.refresh()
                                            }
                                        }
                                    }
                                }
                            }

                            Flickable {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                contentWidth:      width
                                contentHeight:     _sysInfoFlow.implicitHeight
                                    + Theme.AppTheme.marginLg * 2
                                clip:              true
                                boundsBehavior:    Flickable.StopAtBounds

                                Flow {
                                    id: _sysInfoFlow
                                    anchors.left:    parent.left
                                    anchors.right:   parent.right
                                    anchors.top:     parent.top
                                    anchors.margins: Theme.AppTheme.marginLg
                                    spacing:         Theme.AppTheme.spacingMd

                                    Repeater {
                                        model: root.workspaceController
                                            ? (root.workspaceController.overview.sections || []) : []

                                        delegate: PlatformWidgets.OverviewSectionCard {
                                            required property var modelData
                                            title:      modelData.title      || ""
                                            rows:       modelData.rows       || []
                                            emptyState: modelData.emptyState || ""
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ── Right contextual detail panel ─────────────────
                Rectangle {
                    id: _detailPanel
                    Layout.fillHeight:     true
                    Layout.preferredWidth: 288
                    visible:               root._detailOpen
                    color:                 Theme.AppTheme.surface
                    z:                     1

                    Rectangle {
                        anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                        width: 1; color: Theme.AppTheme.divider
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        // Panel header — ContextualActionToolbar for module actions
                        AppWidgets.ContextualActionToolbar {
                            Layout.fillWidth: true
                            showBack: true
                            title:    root._activeSection === "modules"
                                ? (root._selectedItem ? (root._selectedItem.title || "Module Detail") : "Module Detail")
                                : (root._selectedItem ? (root._selectedItem.title || "Profile Detail") : "Profile Detail")
                            subtitle: root._selectedItem ? (root._selectedItem.statusLabel || "") : ""
                            busy:     root._busy
                            actions:  root._moduleContextActions
                            onBackRequested: root._selectedRowId = ""
                            onActionTriggered: function(id) {
                                if (id === "lifecycle") {
                                    if (root._selectedItem && root.workspaceController)
                                        lifecycleDialog.openForItem(
                                            root._selectedItem,
                                            root.workspaceController.lifecycleOptions || []
                                        )
                                } else if (id === "licensed") {
                                    if (root.workspaceController)
                                        root.workspaceController.toggleModuleLicensed(root._selectedRowId)
                                } else if (id === "enabled") {
                                    if (root.workspaceController)
                                        root.workspaceController.toggleModuleEnabled(root._selectedRowId)
                                }
                            }
                        }

                        // Panel content
                        Flickable {
                            Layout.fillWidth:  true
                            Layout.fillHeight: true
                            contentWidth:      width
                            contentHeight:     _detailContent.implicitHeight
                            clip:              true
                            boundsBehavior:    Flickable.StopAtBounds

                            ColumnLayout {
                                id: _detailContent
                                width:   parent.width
                                spacing: Theme.AppTheme.spacingSm

                                // Item title
                                Label {
                                    Layout.fillWidth:   true
                                    Layout.leftMargin:  Theme.AppTheme.marginMd
                                    Layout.rightMargin: Theme.AppTheme.marginMd
                                    Layout.topMargin:   Theme.AppTheme.marginMd
                                    text:           root._selectedItem
                                        ? (root._selectedItem.title || "") : ""
                                    color:          Theme.AppTheme.textPrimary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.sectionSize
                                    font.bold:      true
                                    wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                }

                                // Status chip
                                AppWidgets.StatusChip {
                                    Layout.leftMargin: Theme.AppTheme.marginMd
                                    visible: root._selectedItem
                                        ? (root._selectedItem.statusLabel || "").length > 0 : false
                                    status: root._selectedItem
                                        ? (root._selectedItem.statusLabel || "") : ""
                                }

                                Rectangle {
                                    Layout.fillWidth:   true
                                    Layout.leftMargin:  Theme.AppTheme.marginMd
                                    Layout.rightMargin: Theme.AppTheme.marginMd
                                    height: 1; color: Theme.AppTheme.divider
                                }

                                // Stage / license subtitle
                                ColumnLayout {
                                    Layout.fillWidth:   true
                                    Layout.leftMargin:  Theme.AppTheme.marginMd
                                    Layout.rightMargin: Theme.AppTheme.marginMd
                                    spacing: 2
                                    visible: root._selectedItem
                                        ? (root._selectedItem.subtitle || "").length > 0 : false

                                    Label {
                                        text:           root._activeSection === "modules"
                                            ? "Stage / License" : "Details"
                                        color:          Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold:      true
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text:           root._selectedItem
                                            ? (root._selectedItem.subtitle || "") : ""
                                        color:          Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                    }
                                }

                                // Runtime / capabilities metaText
                                ColumnLayout {
                                    Layout.fillWidth:   true
                                    Layout.leftMargin:  Theme.AppTheme.marginMd
                                    Layout.rightMargin: Theme.AppTheme.marginMd
                                    spacing: 2
                                    visible: root._selectedItem
                                        ? (root._selectedItem.metaText || "").length > 0 : false

                                    Label {
                                        text:           root._activeSection === "modules"
                                            ? "Runtime" : "Info"
                                        color:          Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold:      true
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text:           root._selectedItem
                                            ? (root._selectedItem.metaText || "") : ""
                                        color:          Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                    }
                                }

                            }
                        }
                    }
                }
            }
        }
    }

    // ── Module lifecycle dialog (wiring unchanged) ────────────────
    PlatformDialogs.ModuleLifecycleDialog {
        id: lifecycleDialog

        onStatusConfirmed: function(moduleCode, lifecycleStatus) {
            if (root.workspaceController !== null)
                root.workspaceController.changeModuleLifecycleStatus(moduleCode, lifecycleStatus)
            lifecycleDialog.close()
        }
    }
}
