pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import "../components"

// Roles & Access — scoped access grant detail page.
// Follows the shared Admin list/detail pattern (SectionDetailPage + section-aware
// ContextualActionToolbar + lazy sections). Opened additively when a grant row is
// activated in AccessSecurityPanel; the panel remains the list / assignment surface.
//
// Section data is sourced from the flat grant view-model exposed by
// PlatformAdminAccessWorkspaceController.scopeGrants (the controller does not expose
// per-grant user/session breakdowns), so sections are Overview / Permissions / Scope /
// Audit. Entity actions (Revoke) appear only on Overview; non-overview sections show
// section-specific actions only.
Item {
    id: root

    property PlatformControllers.PlatformAdminAccessWorkspaceController controller: null
    property string grantId: ""
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()

    readonly property var _grant: {
        const id = root.grantId
        if (!id || !root.controller) return ({})
        const items = root.controller.scopeGrants ? (root.controller.scopeGrants.items || []) : []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return ({})
    }

    readonly property string _title: String(root._grant && root._grant.title ? root._grant.title : "Access Grant")
    readonly property string _status: String(root._grant && root._grant.statusLabel ? root._grant.statusLabel : "")
    readonly property string _username: String(root._grant && root._grant.subtitle ? root._grant.subtitle : "")
    readonly property string _permissions: String(root._grant && root._grant.supportingText ? root._grant.supportingText : "")
    readonly property string _assigned: String(root._grant && root._grant.metaText ? root._grant.metaText : "")

    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Permissions" },
        { "label": "Scope" },
        { "label": "Audit" }
    ]
    readonly property string _activeSectionLabel: {
        const section = root._sections[root.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property string _toolbarSubtitle: {
        switch (root._activeSectionLabel) {
        case "Overview":    return "Principal, role, and scope binding for this access grant."
        case "Permissions": return "Effective permissions implied by the assigned role."
        case "Scope":       return "The organizational scope this grant applies to."
        case "Audit":       return "Access change history stays centralized in the shared audit workspace."
        default:            return ""
        }
    }
    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview") {
            return [
                { "id": "revoke",  "label": "Revoke",  "icon": "delete",  "danger": true },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
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
        { "label": "Principal", "value": root._grant.title },
        { "label": "Username",  "value": root._username },
        { "label": "Role",      "value": root._status },
        { "label": "Scope",     "value": root._assigned },
        { "label": "Grant ID",  "value": root.grantId }
    ]

    function _handleAction(actionId) {
        if (!root.controller) return
        if (actionId === "revoke") {
            if (root.grantId.length > 0) {
                root.controller.removeMembership(root.grantId)
                root.backRequested()
            }
        } else if (actionId === "refresh") {
            root.controller.refresh()
        }
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
        onSectionChanged: function(index) { root.activeSectionIndex = index }

        AppWidgets.InlineMessage {
            width: parent ? parent.width : root.width
            visible: root.errorMessage.length > 0
            tone: "danger"
            message: root.errorMessage
        }

        AppWidgets.InlineMessage {
            width: parent ? parent.width : root.width
            visible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
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
            onActionTriggered: function(actionId) { root._handleAction(actionId) }
        }

        // ── Overview ──────────────────────────────────────────────
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
                loadingMessage: "Loading grant overview..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading { width: parent.width; label: "Overview" }

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
                                    title: "Grant Summary"
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
                                                id: _field
                                                required property var modelData
                                                Layout.fillWidth: true
                                                spacing: 2

                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: String(_field.modelData.label || "")
                                                    color: Theme.AppTheme.textMuted
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    font.bold: true
                                                }

                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: _field.modelData.value === undefined || _field.modelData.value === null || String(_field.modelData.value).length === 0
                                                        ? "-"
                                                        : String(_field.modelData.value)
                                                    color: Theme.AppTheme.textPrimary
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
            }
        }

        // ── Permissions ───────────────────────────────────────────
        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 1 ? permissionsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: permissionsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading permissions..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading { width: parent.width; label: "Permissions" }

                        Item {
                            width: parent.width
                            implicitHeight: permColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: permColumn
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
                                    message: "Permissions are derived from the assigned role. Manage role definitions in the shared access governance services."
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: permBody.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Effective Permissions"
                                    outlined: true

                                    ColumnLayout {
                                        id: permBody
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: root._permissions.length > 0
                                                ? root._permissions
                                                : "No explicit permission summary is exposed for this grant."
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

        // ── Scope ─────────────────────────────────────────────────
        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 2 ? scopeLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: scopeLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 2
                keepLoaded: true
                loadingMessage: "Loading scope..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Scope"
                        infoMessage: "This grant applies to the scope shown below; scope membership is governed by the shared platform hierarchy."
                        cardTitle: "Scope Binding"
                        notes: [
                            root._assigned.length > 0 ? root._assigned : "No scope detail is exposed for this grant.",
                            "Use the assignment panel to re-scope or reassign access."
                        ]
                    }
                }
            }
        }

        // ── Audit ─────────────────────────────────────────────────
        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 3 ? auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 3
                keepLoaded: true
                loadingMessage: "Loading audit guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Audit"
                        infoMessage: "Access change history stays centralized in the shared audit workspace."
                        cardTitle: "Audit Boundary"
                        notes: [
                            "Use the Audit workspace for grant/revoke history and actor inspection.",
                            "Access detail pages link into shared audit flows rather than duplicating audit storage."
                        ]
                    }
                }
            }
        }
    }
}
