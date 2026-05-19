pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

Rectangle {
    id: drawer

    property ShellContexts.ShellContext shellModel
    property bool collapsed: false

    implicitWidth: drawer.collapsed ? 48 : 240

    Behavior on implicitWidth {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    color: Theme.AppTheme.navBackground

    // Per-route icon — granular workspace identity
    function iconForRoute(routeId) {
        const m = {
            "shell.home":                              "home",
            "platform.admin":                          "admin",
            "platform.control":                        "control",
            "platform.settings":                       "settings",
            "project_management.projects":             "project",
            "project_management.tasks":                "tasks",
            "project_management.scheduling":           "calendar",
            "project_management.resources":            "resources",
            "project_management.financials":           "financials",
            "project_management.risk":                 "risk",
            "project_management.portfolio":            "portfolio",
            "project_management.register":             "register",
            "project_management.collaboration":        "collaboration",
            "project_management.timesheets":           "timesheets",
            "project_management.dashboard":            "dashboard",
            "maintenance_management.dashboard":        "dashboard",
            "maintenance_management.assets":           "assets",
            "maintenance_management.work_requests":    "workflow",
            "maintenance_management.work_orders":      "register",
            "maintenance_management.preventive":       "calendar",
            "maintenance_management.reliability":      "reliability",
            "maintenance_management.planner":          "planner",
            "inventory_procurement.dashboard":         "dashboard",
            "inventory_procurement.catalog":           "catalog",
            "inventory_procurement.inventory":         "inventory",
            "inventory_procurement.reservations":      "reservations",
            "inventory_procurement.procurement":       "procurement",
            "inventory_procurement.pricing":           "pricing"
        }
        return m[routeId] || "default"
    }

    // State
    property string _filter: ""
    property var _collapsed: ({})

    function _isMod(mod) { return Boolean(drawer._collapsed[mod]) }
    function _toggleMod(mod) {
        const s = drawer._collapsed
        s[mod] = !Boolean(s[mod])
        drawer._collapsed = Object.assign({}, s)
    }

    // Flat render list: [{type:"module"|"item", moduleLabel, routeId, title, icon}]
    readonly property var _renderList: {
        const nav = drawer.shellModel ? drawer.shellModel.navigationItems : []
        const lo = drawer._filter.toLowerCase()
        const result = []
        const seenMod = {}

        for (let i = 0; i < nav.length; i++) {
            const it = nav[i]
            if (lo.length > 0 && String(it.title).toLowerCase().indexOf(lo) < 0) {
                continue
            }
            const mod = String(it.moduleLabel || "")
            if (mod.length > 0 && mod !== "Shell" && !seenMod[mod]) {
                seenMod[mod] = true
                result.push({ type: "module", moduleLabel: mod })
            }
            const hidden = mod !== "Shell" && drawer._isMod(mod) && lo.length === 0
            if (!hidden) {
                result.push({
                    type: "item",
                    moduleLabel: mod,
                    routeId: String(it.routeId),
                    title: String(it.title),
                    icon: drawer.iconForRoute(String(it.routeId))
                })
            }
        }
        return result
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Search bar (hidden when collapsed) ──────────────────────
        Item {
            Layout.fillWidth: true
            height: drawer.collapsed ? 0 : 36
            clip: true

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingXs

                AppIcons.AppIcon {
                    name: "search"
                    size: 11
                    iconColor: Theme.AppTheme.textMuted
                }

                TextField {
                    id: filterField
                    Layout.fillWidth: true
                    text: drawer._filter
                    onTextChanged: drawer._filter = text
                    placeholderText: "Filter…"
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    color: Theme.AppTheme.textPrimary
                    leftPadding: 0
                    rightPadding: 0
                    topPadding: 0
                    bottomPadding: 0
                    background: Item {}
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.AppTheme.divider
            visible: !drawer.collapsed
        }

        Item { Layout.fillWidth: true; height: Theme.AppTheme.spacingXs }

        // ── Navigation list ─────────────────────────────────────────
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: drawer.implicitWidth
                spacing: 0

                Repeater {
                    model: drawer._renderList

                    delegate: Item {
                        id: navDelegate
                        required property var modelData

                        readonly property bool isHdr: navDelegate.modelData.type === "module"
                        readonly property bool isSelected: !navDelegate.isHdr
                            && drawer.shellModel !== null
                            && drawer.shellModel.currentRouteId === navDelegate.modelData.routeId

                        Layout.fillWidth: true
                        height: navDelegate.isHdr
                            ? (drawer.collapsed
                                ? 0
                                : Theme.AppTheme.captionSize + Theme.AppTheme.spacingLg)
                            : Theme.AppTheme.sidebarRowHeight
                        clip: true

                        // ── Module section header ────────────────────
                        Item {
                            anchors.fill: parent
                            visible: navDelegate.isHdr && !drawer.collapsed

                            RowLayout {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.leftMargin: Theme.AppTheme.marginLg
                                anchors.rightMargin: Theme.AppTheme.marginMd
                                anchors.bottomMargin: Theme.AppTheme.spacingXs
                                spacing: 0

                                Label {
                                    Layout.fillWidth: true
                                    text: (navDelegate.modelData.moduleLabel || "").toUpperCase()
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                    font.letterSpacing: 0.8
                                    elide: Text.ElideRight
                                }

                                AppIcons.AppIcon {
                                    name: drawer._isMod(navDelegate.modelData.moduleLabel)
                                        ? "chevron_right" : "chevron_down"
                                    size: 9
                                    iconColor: Theme.AppTheme.textMuted
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: drawer._toggleMod(navDelegate.modelData.moduleLabel)
                            }
                        }

                        // ── Nav item row ─────────────────────────────
                        Item {
                            anchors.fill: parent
                            visible: !navDelegate.isHdr

                            Rectangle {
                                anchors.fill: parent
                                color: navDelegate.isSelected
                                    ? Theme.AppTheme.navSelectedBackground
                                    : rowHover.containsMouse
                                        ? Theme.AppTheme.navHoverBackground
                                        : "transparent"

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    width: 3
                                    radius: 1
                                    color: Theme.AppTheme.accent
                                    visible: navDelegate.isSelected
                                }
                            }

                            // Collapsed: centered icon + tooltip
                            AppIcons.AppIcon {
                                anchors.centerIn: parent
                                visible: drawer.collapsed
                                name: navDelegate.modelData.icon || "default"
                                size: 16
                                iconColor: navDelegate.isSelected
                                    ? Theme.AppTheme.navSelectedText
                                    : Theme.AppTheme.textMuted
                            }

                            // Expanded: icon + label
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: navDelegate.isSelected
                                    ? Theme.AppTheme.marginLg - 3
                                    : Theme.AppTheme.marginLg
                                anchors.rightMargin: Theme.AppTheme.marginMd
                                spacing: Theme.AppTheme.spacingSm
                                visible: !drawer.collapsed

                                AppIcons.AppIcon {
                                    name: navDelegate.modelData.icon || "default"
                                    size: 14
                                    iconColor: navDelegate.isSelected
                                        ? Theme.AppTheme.navSelectedText
                                        : Theme.AppTheme.textMuted
                                }

                                Label {
                                    Layout.fillWidth: true
                                    text: navDelegate.modelData.title || ""
                                    color: navDelegate.isSelected
                                        ? Theme.AppTheme.navSelectedText
                                        : Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.bold: navDelegate.isSelected
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                id: rowHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (drawer.shellModel) {
                                        drawer.shellModel.selectRoute(navDelegate.modelData.routeId)
                                    }
                                }
                            }

                            ToolTip {
                                visible: drawer.collapsed && rowHover.containsMouse
                                text: navDelegate.modelData.title || ""
                                delay: 350
                            }
                        }
                    }
                }

                Item { Layout.fillWidth: true; height: Theme.AppTheme.spacingMd }
            }
        }

        // ── Bottom collapse toggle ───────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: 36
            color: collapseHover.containsMouse
                ? Theme.AppTheme.navHoverBackground
                : "transparent"

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: Theme.AppTheme.divider
            }

            // Collapsed: single chevron centered
            AppIcons.AppIcon {
                anchors.centerIn: parent
                visible: drawer.collapsed
                name: "chevron_right"
                size: 10
                iconColor: Theme.AppTheme.textMuted
            }

            // Expanded: "Collapse" label + chevron
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.marginLg
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm
                visible: !drawer.collapsed

                Label {
                    Layout.fillWidth: true
                    text: "Collapse sidebar"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }

                AppIcons.AppIcon {
                    name: "chevron_left"
                    size: 10
                    iconColor: Theme.AppTheme.textMuted
                }
            }

            MouseArea {
                id: collapseHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: drawer.collapsed = !drawer.collapsed
            }

            ToolTip {
                visible: collapseHover.containsMouse && drawer.collapsed
                text: "Expand sidebar"
                delay: 350
            }
        }
    }
}
