pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers


ColumnLayout {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    // Duck-typed: PMProjectContextController (kept as `var` so this file
    // doesn't need to import ProjectManagement.Controllers just for a type
    // annotation).
    property var projectContext: null
    property string currentPolicy: "optional"

    spacing: 0

    // Mirrors the exact lookup patterns already proven in production by
    // PlatformWorkspacePage.qml's _activeTenantName/_activeOrganizationName
    // -- tenant items are a flat {id, displayName, tenantCode} list; org
    // items are {items:[{..., state:{isActive, displayName}}]}.
    readonly property var _tenantItems: root.platformCatalog
        ? (root.platformCatalog.tenantSwitcher.tenants || [])
        : []
    readonly property bool _isMultiTenant: root._tenantItems.length > 1
    readonly property string _activeTenantName: {
        if (!root.platformCatalog) {
            return ""
        }
        const activeId = root.platformCatalog.tenantSwitcher.activeTenantId
        for (let i = 0; i < root._tenantItems.length; i += 1) {
            const item = root._tenantItems[i] || {}
            if (item.id === activeId) {
                return String(item.displayName || item.tenantCode || "")
            }
        }
        return ""
    }
    readonly property var _organizationItems: root.platformCatalog
        ? ((root.platformCatalog.adminWorkspace.organizations || {}).items || [])
        : []
    readonly property string _activeOrganizationName: {
        for (let i = 0; i < root._organizationItems.length; i += 1) {
            const item = root._organizationItems[i] || {}
            const state = item.state || {}
            if (state.isActive === true) {
                return String(state.displayName || item.title || "")
            }
        }
        return ""
    }
    readonly property var _tenantOptions: {
        const options = []
        for (let i = 0; i < root._tenantItems.length; i += 1) {
            const item = root._tenantItems[i] || {}
            const id = String(item.id || "")
            if (id.length === 0) {
                continue
            }
            options.push({ "id": id, "label": String(item.displayName || item.tenantCode || id) })
        }
        return options
    }

    AppWidgets.ContextBar {
        Layout.fillWidth: true
        tenantSwitcherVisible: root._isMultiTenant
        tenantName: root._activeTenantName
        tenantOptions: root._tenantOptions
        organizationName: root._activeOrganizationName
        organizationOptions: []

        onTenantSelected: function(tenantId) {
            if (root.platformCatalog) {
                root.platformCatalog.tenantSwitcher.switchToTenant(tenantId)
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: Theme.AppTheme.headerHeight
        color: Theme.AppTheme.surfaceRaised

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.AppTheme.divider
        }

        // R2.13: horizontally scrollable rather than clipped/overflowing --
        // this row's natural width (label + search + results + clear +
        // error text) can exceed available width once the shell drawer and
        // PM nav rail are both expanded at/near 1024px content width.
        Flickable {
            anchors.fill: parent
            anchors.leftMargin: Theme.AppTheme.marginMd
            anchors.rightMargin: Theme.AppTheme.marginMd
            contentWidth: _projectRow.implicitWidth
            contentHeight: height
            boundsBehavior: Flickable.StopAtBounds
            clip: true

        RowLayout {
            id: _projectRow
            height: parent.height
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                text: "Project:"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }

            AppControls.Label {
                Layout.preferredWidth: 160
                text: root.projectContext && root.projectContext.hasActiveProject
                    ? root.projectContext.activeProjectLabel
                    : "All projects"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
                elide: Text.ElideRight
            }

            // Authoritative, server-searched selector (PMProjectContextController.
            // searchProjects()/projectOptions) -- never an unbounded local snapshot.
            AppControls.SearchField {
                id: _projectSearch
                Layout.preferredWidth: 220
                placeholderText: "Search projects..."
                enabled: root.projectContext !== null
                onSearchTriggered: function(text) {
                    if (root.projectContext) root.projectContext.searchProjects(text)
                }
            }

            AppControls.ComboBox {
                id: _projectResults
                Layout.preferredWidth: 220
                textRole: "label"
                model: root.projectContext ? root.projectContext.projectOptions : []
                enabled: root.projectContext !== null && _projectResults.count > 0

                onActivated: function(index) {
                    const options = root.projectContext ? root.projectContext.projectOptions : []
                    const option = options[index]
                    if (option && root.projectContext) {
                        // Explicit pinning action (R2.10) -- picking a
                        // result here is the only thing that sets the
                        // shared active project; typing/searching alone
                        // never does.
                        root.projectContext.selectProject(String(option.id || ""))
                    }
                }
            }

            AppControls.SecondaryButton {
                text: "Clear"
                visible: root.projectContext ? root.projectContext.hasActiveProject : false
                onClicked: if (root.projectContext) root.projectContext.clearProject()
            }

            AppControls.Label {
                Layout.leftMargin: Theme.AppTheme.spacingMd
                visible: root.projectContext ? root.projectContext.errorMessage.length > 0 : false
                text: root.projectContext ? root.projectContext.errorMessage : ""
                color: Theme.AppTheme.danger
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
            }
        }
        }
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.currentPolicy === "required" && !(root.projectContext && root.projectContext.hasActiveProject)
        tone: "warning"
        message: "This workspace requires an active project."
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.projectContext ? root.projectContext.validationStatus === "stale" : false
        tone: "danger"
        message: "The active project is no longer available and was cleared."
    }
}
