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

    implicitWidth: drawer.collapsed
        ? Theme.AppTheme.sidebarCollapsedWidth
        : Theme.AppTheme.sidebarWidth

    Behavior on implicitWidth {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    color: Theme.AppTheme.navBackground

    function iconForRoute(routeId) {
        const icons = {
            "shell.home": "home",
            "platform.admin": "admin",
            "platform.control": "control",
            "platform.settings": "settings",
            "project_management.projects": "project",
            "project_management.tasks": "tasks",
            "project_management.scheduling": "calendar",
            "project_management.resources": "resources",
            "project_management.financials": "financials",
            "project_management.risk": "risk",
            "project_management.portfolio": "portfolio",
            "project_management.register": "register",
            "project_management.collaboration": "collaboration",
            "project_management.timesheets": "timesheets",
            "project_management.dashboard": "dashboard",
            "maintenance_management.dashboard": "dashboard",
            "maintenance_management.assets": "assets",
            "maintenance_management.work_requests": "workflow",
            "maintenance_management.work_orders": "register",
            "maintenance_management.preventive": "calendar",
            "maintenance_management.reliability": "reliability",
            "maintenance_management.planner": "planner",
            "inventory_procurement.dashboard": "dashboard",
            "inventory_procurement.catalog": "catalog",
            "inventory_procurement.inventory": "inventory",
            "inventory_procurement.reservations": "reservations",
            "inventory_procurement.procurement": "procurement",
            "inventory_procurement.pricing": "pricing"
        }
        return icons[routeId] || "default"
    }

    property string _filter: ""
    property var _collapsedGroups: ({})

    function _isCollapsed(moduleLabel) {
        return Boolean(drawer._collapsedGroups[moduleLabel])
    }

    function _toggleModule(moduleLabel) {
        const nextState = drawer._collapsedGroups
        nextState[moduleLabel] = !Boolean(nextState[moduleLabel])
        drawer._collapsedGroups = Object.assign({}, nextState)
    }

    readonly property var _renderList: {
        const navItems = drawer.shellModel ? drawer.shellModel.navigationItems : []
        const search = drawer._filter.toLowerCase()
        const list = []
        const seenModules = {}

        for (let i = 0; i < navItems.length; i += 1) {
            const item = navItems[i]
            if (search.length > 0 && String(item.title).toLowerCase().indexOf(search) < 0) {
                continue
            }
            const moduleLabel = String(item.moduleLabel || "")
            if (moduleLabel.length > 0 && moduleLabel !== "Shell" && !seenModules[moduleLabel]) {
                seenModules[moduleLabel] = true
                list.push({ type: "module", moduleLabel: moduleLabel })
            }
            const hidden = moduleLabel !== "Shell" && drawer._isCollapsed(moduleLabel) && search.length === 0
            if (!hidden) {
                list.push({
                    type: "item",
                    moduleLabel: moduleLabel,
                    routeId: String(item.routeId),
                    title: String(item.title),
                    icon: drawer.iconForRoute(String(item.routeId))
                })
            }
        }
        return list
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: drawer.collapsed
                ? Theme.AppTheme.spacingSm
                : Theme.AppTheme.marginMd
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.marginMd
            Layout.rightMargin: Theme.AppTheme.marginMd
            Layout.preferredHeight: drawer.collapsed ? 0 : Theme.AppTheme.inputHeight
            radius: Theme.AppTheme.radiusSm
            color: Theme.AppTheme.surfaceOverlay
            visible: !drawer.collapsed
            clip: true

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.spacingSm
                anchors.rightMargin: Theme.AppTheme.spacingSm
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
                    placeholderText: "Filter navigation"
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

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: drawer.collapsed
                ? Theme.AppTheme.spacingSm
                : Theme.AppTheme.spacingMd
        }

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

                        readonly property bool isHeader: navDelegate.modelData.type === "module"
                        readonly property bool isSelected: !navDelegate.isHeader
                            && drawer.shellModel !== null
                            && drawer.shellModel.currentRouteId === navDelegate.modelData.routeId

                        Layout.fillWidth: true
                        height: navDelegate.isHeader
                            ? (drawer.collapsed ? 0 : Theme.AppTheme.captionSize + Theme.AppTheme.spacingLg)
                            : Theme.AppTheme.sidebarRowHeight
                        clip: true

                        Item {
                            anchors.fill: parent
                            visible: navDelegate.isHeader && !drawer.collapsed

                            RowLayout {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.leftMargin: Theme.AppTheme.marginMd
                                anchors.rightMargin: Theme.AppTheme.marginMd
                                anchors.bottomMargin: Theme.AppTheme.spacingXs
                                spacing: Theme.AppTheme.spacingSm

                                Label {
                                    Layout.fillWidth: true
                                    text: (navDelegate.modelData.moduleLabel || "").toUpperCase()
                                    color: Theme.AppTheme.navMutedText
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                    font.letterSpacing: 0.8
                                    elide: Text.ElideRight
                                }

                                AppIcons.AppIcon {
                                    name: drawer._isCollapsed(navDelegate.modelData.moduleLabel)
                                        ? "chevron_right"
                                        : "chevron_down"
                                    size: 9
                                    iconColor: Theme.AppTheme.textMuted
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: drawer._toggleModule(navDelegate.modelData.moduleLabel)
                            }
                        }

                        Item {
                            anchors.fill: parent
                            visible: !navDelegate.isHeader

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: Theme.AppTheme.spacingSm
                                anchors.rightMargin: Theme.AppTheme.spacingSm
                                height: Theme.AppTheme.sidebarRowHeight - 4
                                radius: Theme.AppTheme.radiusSm
                                color: navDelegate.isSelected
                                    ? Theme.AppTheme.navSelectedBackground
                                    : rowHover.containsMouse
                                        ? Theme.AppTheme.navHoverBackground
                                        : "transparent"
                            }

                            Rectangle {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                anchors.topMargin: 6
                                anchors.bottomMargin: 6
                                width: 3
                                radius: 2
                                color: Theme.AppTheme.accent
                                visible: navDelegate.isSelected
                            }

                            AppIcons.AppIcon {
                                anchors.centerIn: parent
                                visible: drawer.collapsed
                                name: navDelegate.modelData.icon || "default"
                                size: 15
                                iconColor: navDelegate.isSelected
                                    ? Theme.AppTheme.navSelectedText
                                    : Theme.AppTheme.textMuted
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.AppTheme.marginMd
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
                                    font.pixelSize: Theme.AppTheme.smallSize
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
                                delay: 300
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: Theme.AppTheme.marginSm
            Layout.rightMargin: Theme.AppTheme.marginSm
            Layout.bottomMargin: Theme.AppTheme.marginSm
            Layout.preferredHeight: Theme.AppTheme.toolbarHeight
            radius: Theme.AppTheme.radiusSm
            color: collapseHover.containsMouse
                ? Theme.AppTheme.navHoverBackground
                : "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.marginMd
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

            AppIcons.AppIcon {
                anchors.centerIn: parent
                visible: drawer.collapsed
                name: "chevron_right"
                size: 10
                iconColor: Theme.AppTheme.textMuted
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
                delay: 300
            }
        }
    }
}
