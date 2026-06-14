pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "../components"

Item {
    id: root

    property var user: ({})
    property var moduleEntitlementCatalog: ({ "items": [], "emptyState": "No module entitlements are available yet." })
    property var moduleEntitlementColumns: []
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)

    readonly property var _state: (root.user && root.user.state) ? root.user.state : ({})
    readonly property string _title: String(root.user && root.user.title ? root.user.title : "User")
    readonly property string _status: String(root.user && root.user.statusLabel ? root.user.statusLabel : "")
    readonly property string _subtitle: String(root.user && root.user.subtitle ? root.user.subtitle : "")
    readonly property string _securityPosture: String(root.user && root.user.metaText ? root.user.metaText : "")
    readonly property bool _isActive: root._state.currentIsActive === true || root._state.isActive === true
    readonly property var _roleNames: root._state.currentRoleNames || root._state.roleNames || []
    readonly property var _moduleRows: root.moduleEntitlementCatalog.items || []
    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Roles & Access", "count": root._roleNames.length },
        { "label": "Sessions" },
        { "label": "Module Access", "count": root._moduleRows.length },
        { "label": "Audit" }
    ]
    readonly property string _activeSectionLabel: {
        const section = root._sections[root.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property string _toolbarSubtitle: {
        switch (root._activeSectionLabel) {
        case "Overview":
            return root._subtitle
        case "Roles & Access":
            return "Shared platform roles, scoped access, and account posture for the selected identity."
        case "Sessions":
            return "Session governance and lockout posture remain governed by shared platform security services."
        case "Module Access":
            return "Effective access depends on both identity governance and organization-level module entitlement state."
        case "Audit":
            return "Identity audit trails stay centralized in the shared audit workspace."
        default:
            return ""
        }
    }
    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview") {
            return [
                { "id": "edit", "label": "Edit", "icon": "edit" },
                { "id": "toggle_active", "label": root._isActive ? "Set Inactive" : "Set Active", "icon": "approve" },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Roles & Access" || root._activeSectionLabel === "Sessions") {
            return [
                { "id": "show_access", "label": "Open Access", "icon": "chevron_right" }
            ]
        }
        if (root._activeSectionLabel === "Audit") {
            return [
                { "id": "show_audit", "label": "Open Audit", "icon": "chevron_right" }
            ]
        }
        return [
            { "id": "refresh", "label": "Refresh", "icon": "refresh" }
        ]
    }
    readonly property var _overviewFields: [
        { "label": "Username", "value": root._state.username },
        { "label": "Display Name", "value": root._state.displayName || root.user.title },
        { "label": "Email", "value": root._state.email },
        { "label": "Status", "value": root._status },
        { "label": "Active", "value": root._isActive },
        { "label": "User ID", "value": root._state.userId }
    ]

    function _tableHeightForCount(count) {
        const visibleRows = Math.max(1, Math.min(count, 8))
        return Theme.AppTheme.headerHeight + (visibleRows * Theme.AppTheme.normalRowHeight) + Theme.AppTheme.spacingLg
    }

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: root._title
        isBusy: root.busy
        showEdit: false
        showDelete: false
        sections: root._sections

        onBackRequested: root.backRequested()
        onSectionChanged: function(index) {
            root.activeSectionIndex = index
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : root.width
            requestedVisible: root.errorMessage.length > 0
            tone: "danger"
            message: root.errorMessage
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : root.width
            requestedVisible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
            tone: "success"
            message: root.feedbackMessage
        }

        AppWidgets.ContextualActionToolbar {
            detailPagePinned: true
            width: parent ? parent.width : root.width
            title: root._activeSectionLabel
            subtitle: root._toolbarSubtitle
            busy: root.busy
            actions: root._toolbarActions
            onActionTriggered: function(actionId) {
                root.actionRequested(actionId)
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 0 ? overviewLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: overviewLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 0
                keepLoaded: true
                loadingMessage: "Loading user overview..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Overview"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: overviewColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: overviewColumn
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.topMargin: Theme.AppTheme.spacingMd
                                anchors.leftMargin: Theme.AppTheme.spacingMd
                                anchors.rightMargin: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: overviewGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Identity Summary"
                                    outlined: true

                                    GridLayout {
                                        id: overviewGrid
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        columns: 2
                                        columnSpacing: Theme.AppTheme.spacingLg
                                        rowSpacing: Theme.AppTheme.spacingSm

                                        Repeater {
                                            model: root._overviewFields

                                            delegate: ColumnLayout {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                spacing: 2

                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: String(modelData.label || "")
                                                    color: Theme.AppTheme.textMuted
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    font.bold: true
                                                }

                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: modelData.value === undefined || modelData.value === null || String(modelData.value).length === 0
                                                        ? "-"
                                                        : (typeof modelData.value === "boolean" ? (modelData.value ? "Yes" : "No") : String(modelData.value))
                                                    color: Theme.AppTheme.textPrimary
                                                    font.pixelSize: Theme.AppTheme.smallSize
                                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                                }
                                            }
                                        }
                                    }
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: postureColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Security Posture"
                                    outlined: true

                                    ColumnLayout {
                                        id: postureColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: root._securityPosture.length > 0
                                                ? root._securityPosture
                                                : "No additional security posture flags are currently exposed on this record."
                                            color: Theme.AppTheme.textSecondary
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 1 ? rolesLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: rolesLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading roles and access posture..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Roles & Access"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: rolesColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: rolesColumn
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.topMargin: Theme.AppTheme.spacingMd
                                anchors.leftMargin: Theme.AppTheme.spacingMd
                                anchors.rightMargin: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.InlineMessage {
                                    Layout.fillWidth: true
                                    tone: "info"
                                    message: "Role membership is sourced from shared identity, while scoped access grants remain governed by the Platform Access workspace."
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: roleList.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Assigned Roles"
                                    outlined: true

                                    ColumnLayout {
                                        id: roleList
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        Repeater {
                                            model: root._roleNames

                                            delegate: AppControls.Label {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                text: String(modelData || "").replace(/_/g, " ")
                                                color: Theme.AppTheme.textPrimary
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                            }
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            visible: (root._roleNames || []).length === 0
                                            text: "No roles are currently assigned."
                                            color: Theme.AppTheme.textSecondary
                                            font.pixelSize: Theme.AppTheme.smallSize
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 2 ? sessionsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: sessionsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 2
                keepLoaded: true
                loadingMessage: "Loading session guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Sessions"
                        infoMessage: "Session controls, lockouts, and credential posture stay centralized in shared platform security."
                        cardTitle: "Session Governance"
                        notes: [
                            root._securityPosture.length > 0 ? root._securityPosture : "No explicit session posture is currently exposed on this record.",
                            "Use the Access workspace for role and scope governance rather than duplicating session-control workflows here.",
                            "Platform security policies remain the source of truth for session expiry, lockout behavior, and elevated-access posture."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 3 ? modulesLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: modulesLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 3
                keepLoaded: true
                loadingMessage: "Loading module access posture..."
                sourceComponent: Component {
                    AdminDetailTableSection {
                        sectionLabel: "Module Access"
                        infoMessage: "Effective module access depends on both user role/scope and organization-level module entitlement state."
                        emptyTitle: "No module entitlements available"
                        emptyMessage: root.moduleEntitlementCatalog.emptyState || "No module entitlements are available yet."
                        rows: root._moduleRows
                        columns: root.moduleEntitlementColumns
                        loading: root.busy
                        tableHeight: root._tableHeightForCount(root._moduleRows.length)
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 4 ? auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 4
                keepLoaded: true
                loadingMessage: "Loading audit guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Audit"
                        infoMessage: "Identity audit trails stay centralized in the shared audit workspace."
                        cardTitle: "Audit Boundary"
                        notes: [
                            "Use the Audit workspace for actor history, security events, and source payload inspection.",
                            "User detail pages should link into shared audit flows rather than duplicate audit storage."
                        ]
                    }
                }
            }
        }
    }
}
