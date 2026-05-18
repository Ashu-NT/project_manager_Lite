pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Layouts 1.0 as AppLayouts
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ShellContexts.ShellContext shellModel

    title: root.shellModel && root.shellModel.userDisplayName
        ? ("Welcome, " + root.shellModel.userDisplayName)
        : "Welcome"
    subtitle: "Select a module to open its workspaces, or use the sidebar to navigate directly."

    // Build module summary list from navigationItems (exclude Shell home entry)
    readonly property var _modules: {
        const items = root.shellModel ? (root.shellModel.navigationItems || []) : []
        const moduleMap = {}
        const moduleOrder = []
        for (let i = 0; i < items.length; i++) {
            const item = items[i]
            const mod = String(item.moduleLabel || "")
            if (mod === "Shell") continue
            if (!moduleMap[mod]) {
                moduleMap[mod] = {
                    "label": mod,
                    "count": 0,
                    "primaryRouteId": "",
                    "dashboardRouteId": ""
                }
                moduleOrder.push(mod)
            }
            moduleMap[mod].count += 1
            if (!moduleMap[mod].primaryRouteId) {
                moduleMap[mod].primaryRouteId = String(item.routeId || "")
            }
            if (String(item.routeId || "").indexOf("dashboard") >= 0 && !moduleMap[mod].dashboardRouteId) {
                moduleMap[mod].dashboardRouteId = String(item.routeId || "")
            }
        }
        return moduleOrder.map(function(mod) { return moduleMap[mod] })
    }

    function iconForModule(moduleLabel) {
        const s = String(moduleLabel || "").toLowerCase()
        if (s.indexOf("project") >= 0) return "project"
        if (s.indexOf("maintenance") >= 0) return "assets"
        if (s.indexOf("inventory") >= 0 || s.indexOf("procurement") >= 0) return "inventory"
        return "admin"
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            id: homeLayout
            width: parent.width
            spacing: Theme.AppTheme.spacingLg

            // Summary metrics row
            Flow {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.MetricCard {
                    width: homeLayout.width >= 720
                        ? Math.floor((homeLayout.width - Theme.AppTheme.spacingMd * 3) / 4)
                        : Math.floor((homeLayout.width - Theme.AppTheme.spacingMd) / 2)
                    label: "Modules"
                    value: root._modules.length + ""
                    supportingText: "Active business modules"
                }

                AppWidgets.MetricCard {
                    width: homeLayout.width >= 720
                        ? Math.floor((homeLayout.width - Theme.AppTheme.spacingMd * 3) / 4)
                        : Math.floor((homeLayout.width - Theme.AppTheme.spacingMd) / 2)
                    label: "Workspaces"
                    value: root.shellModel ? (root.shellModel.navigationItems.length - 1) + "" : "0"
                    supportingText: "Total navigable workspaces"
                }
            }

            // Section label
            Label {
                Layout.fillWidth: true
                text: "Modules"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }

            // Module tiles grid
            Flow {
                id: modulesFlow
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                Repeater {
                    model: root._modules

                    delegate: Item {
                        id: moduleDelegate
                        required property var modelData

                        readonly property string targetRoute: moduleDelegate.modelData.dashboardRouteId
                            || moduleDelegate.modelData.primaryRouteId

                        width: modulesFlow.width >= 720
                            ? Math.floor((modulesFlow.width - Theme.AppTheme.spacingMd) / 2)
                            : modulesFlow.width
                        height: tileForeground.implicitHeight + (Theme.AppTheme.spacingMd * 2)

                        Rectangle {
                            anchors.fill: parent
                            color: tileHover.containsMouse
                                ? Theme.AppTheme.hoverSurface
                                : Theme.AppTheme.surfaceAlt
                            radius: Theme.AppTheme.radiusMd

                            Behavior on color { ColorAnimation { duration: 100 } }
                        }

                        RowLayout {
                            id: tileForeground
                            anchors {
                                left: parent.left
                                right: parent.right
                                verticalCenter: parent.verticalCenter
                                leftMargin: Theme.AppTheme.spacingMd
                                rightMargin: Theme.AppTheme.spacingMd
                            }
                            spacing: Theme.AppTheme.spacingMd

                            Rectangle {
                                width: 40
                                height: 40
                                radius: Theme.AppTheme.radiusMd
                                color: Theme.AppTheme.accentSoft

                                AppIcons.AppIcon {
                                    anchors.centerIn: parent
                                    icon: root.iconForModule(moduleDelegate.modelData.label)
                                    color: Theme.AppTheme.accent
                                    size: 18
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Label {
                                    Layout.fillWidth: true
                                    text: moduleDelegate.modelData.label
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.bold: true
                                    elide: Text.ElideRight
                                }

                                Label {
                                    text: moduleDelegate.modelData.count + " workspaces"
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }

                            Label {
                                text: "›"
                                color: tileHover.containsMouse
                                    ? Theme.AppTheme.accent
                                    : Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: 18

                                Behavior on color { ColorAnimation { duration: 100 } }
                            }
                        }

                        HoverHandler { id: tileHover }

                        TapHandler {
                            onTapped: {
                                if (root.shellModel && moduleDelegate.targetRoute) {
                                    root.shellModel.selectRoute(moduleDelegate.targetRoute)
                                }
                            }
                        }
                    }
                }
            }

            // App info footer
            Label {
                Layout.fillWidth: true
                Layout.topMargin: Theme.AppTheme.spacingSm
                text: root.shellModel ? root.shellModel.appTitle + " — Enterprise Asset & Project Management" : ""
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode: Text.WordWrap
            }
        }
    }
}
