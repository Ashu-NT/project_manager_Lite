pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import workspaces.parties.sections 1.0 as PartySections

// Orchestrator only: owns party identity/lifecycle, per-tab state
// (page/search/filter) and data fetching. Each tab's own markup lives in
// workspaces/parties/sections/. Final section set is Overview/Activity --
// Contacts/Customer-Client-Profile/Linked-Projects/Documents/Audit were all
// either placeholder tabs with no real backing capability or data that
// belongs to a consuming module (PM/Procurement), not shared Platform
// identity. See the Party UI modernization notes for the full rationale.
Item {
    id: root
    objectName: "adminPartyDetailPage"

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var party: ({})
    property var breadcrumb: []
    property bool canWrite: true // party.manage -- edit/lifecycle
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)

    readonly property var _state: (root.party && root.party.state) ? root.party.state : ({})
    readonly property string _title: String(root.party && root.party.title ? root.party.title : "Party")
    readonly property var _statusLabelValue: root.party ? root.party.statusLabel : null
    readonly property string _status: (root._statusLabelValue && typeof root._statusLabelValue === "object")
        ? String(root._statusLabelValue.label || "")
        : String(root._statusLabelValue || "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property string _statusTone: root._isActive ? "success" : "neutral"
    readonly property string _partyId: String(root._state.partyId || root._state.id || root.party.id || "")
    readonly property string _organizationId: String(root._state.organizationId || "")

    readonly property string _partyCode: String(root._state.partyCode || "")
    readonly property string _partyTypeLabel: String(root._state.partyTypeLabel || "")
    readonly property string _headerSubtitle: root._joinNonEmpty([root._partyCode, root._partyTypeLabel], "  ·  ")

    function _joinNonEmpty(parts, sep) {
        return parts.filter(function(p) { return String(p || "").trim().length > 0 }).join(sep)
    }
    function _displayValue(value) {
        const text = String(value || "").trim()
        return text.length > 0 ? text : "—"
    }
    function _titleCaseRole(value) {
        return String(value || "").toLowerCase().replace(/_/g, " ").replace(/\b\w/g, function(c) { return c.toUpperCase() })
    }

    // -- Header lifecycle menu: Party's own 2-state lifecycle (Active/
    // Inactive only -- no Archive; see activate_party/deactivate_party, a
    // distinct command pair, not the generic profile update). Mutations
    // bubble up via actionRequested() to PartiesWorkspacePage.qml's
    // handleDetailAction.
    readonly property var _lifecycleMenuItems: {
        const items = [
            { "id": "edit", "label": "Edit party", "icon": "edit", "enabled": root.canWrite },
            { "separator": true }
        ]
        if (root._isActive) {
            items.push({ "id": "deactivate", "label": "Deactivate party", "icon": "reject", "enabled": root.canWrite })
        } else {
            items.push({ "id": "activate", "label": "Activate party", "icon": "approve", "enabled": root.canWrite })
        }
        return items
    }

    // -- Overview: bounded (~5 item) recent activity, distinct from the
    // full paginated Activity tab's own state below.
    property var _recentActivity: []
    function _refreshRecentActivity() {
        if (root._partyId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            root._recentActivity = []
            return
        }
        root._recentActivity = root.platformCatalog.adminWorkspace.partyActivity(root._partyId, root._organizationId) || []
    }

    // -- Activity tab: this party's own paginated, searchable business-
    // activity history.
    property int _activityPage: 1
    property int _activityPageSize: 25
    property string _activitySearch: ""
    property string _activityDateFilter: ""
    property var _activityCatalog: ({
        "items": [], "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0,
        "emptyState": "", "noResultsState": ""
    })
    readonly property var _activityDateFilterOptions: [
        { "value": "", "label": "All time" },
        { "value": "today", "label": "Today" },
        { "value": "7d", "label": "Last 7 days" },
        { "value": "30d", "label": "Last 30 days" }
    ]
    function _refreshActivityPage() {
        if (root._partyId.length === 0 || root._organizationId.length === 0
            || !root.platformCatalog || !root.platformCatalog.adminWorkspace) {
            return
        }
        root._activityCatalog = root.platformCatalog.adminWorkspace.partyActivityPage(
            root._partyId, root._organizationId, root._activityPage, root._activityPageSize,
            root._activitySearch, root._activityDateFilter
        )
    }

    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Activity" }
    ]
    readonly property string _activeSectionLabel: {
        const section = root._sections[root.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    function _indexOfSection(label) {
        for (let i = 0; i < root._sections.length; i += 1) {
            if (root._sections[i].label === label) return i
        }
        return -1
    }
    readonly property string _toolbarSubtitle: root._activeSectionLabel === "Overview"
        ? "Shared external party and counterparty master data."
        : ""
    readonly property var _toolbarActions: root._activeSectionLabel === "Overview"
        ? [{ "id": "refresh", "label": "Refresh", "icon": "refresh" }]
        : []
    readonly property bool _showSectionToolbar: root._activeSectionLabel === "Overview"

    readonly property var _partyInformationFields: [
        { "label": "Party Name", "value": root._displayValue(root._state.partyName || root.party.title) },
        { "label": "Party Code", "value": root._displayValue(root._partyCode) },
        { "label": "Party Type", "value": root._displayValue(root._partyTypeLabel) }
    ]
    readonly property bool _hasLegalRegistrationData: [
        root._state.legalName, root._state.registrationNumber, root._state.taxIdentifier, root._state.externalReference
    ].some(function(v) { return String(v || "").trim().length > 0 })
    readonly property var _legalRegistrationFields: [
        { "label": "Legal Name", "value": root._displayValue(root._state.legalName) },
        { "label": "Registration Number", "value": root._displayValue(root._state.registrationNumber) },
        { "label": "Tax Identifier", "value": root._displayValue(root._state.taxIdentifier) },
        { "label": "External Reference", "value": root._displayValue(root._state.externalReference) }
    ]
    readonly property var _contactFields: [
        { "label": "Contact Name", "value": root._displayValue(root._state.contactName) },
        { "label": "Email", "value": root._displayValue(root._state.email) },
        { "label": "Phone", "value": root._displayValue(root._state.phone) },
        { "label": "Website", "value": root._displayValue(root._state.website) }
    ]
    readonly property var _addressFields: [
        { "label": "Address Line 1", "value": root._displayValue(root._state.addressLine1) },
        { "label": "Address Line 2", "value": root._displayValue(root._state.addressLine2) },
        { "label": "City", "value": root._displayValue(root._state.city) },
        { "label": "Postal Code", "value": root._displayValue(root._state.postalCode) },
        { "label": "Country", "value": root._displayValue(root._state.country) }
    ]
    readonly property var _businessRoles: {
        const roles = root._state.roles || []
        return roles.map(function(r) { return root._titleCaseRole(r) })
    }
    // No Open Related Projects/Open Supplier Profile/Open Customer Account
    // entries yet -- those require real, approved cross-module navigation
    // targets that don't exist today (see the audit's own finding on
    // Project.client_party_id being a real backend relationship but an
    // incomplete UI integration point). View Activity is local navigation,
    // not an "action" in the cross-module sense, so it isn't listed here
    // either (Recent Activity's own "View all" link already covers it).
    readonly property var _relatedActions: []

    onPartyChanged: {
        root._refreshActivityPage()
        root._refreshRecentActivity()
    }
    Component.onCompleted: {
        root._refreshActivityPage()
        root._refreshRecentActivity()
    }

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: root._title
        statusLabel: root._status
        statusTone: root._statusTone
        subtitleLine: root._headerSubtitle
        breadcrumb: root.breadcrumb
        isBusy: root.busy
        showEdit: root.canWrite
        showDelete: false
        menuActions: root._lifecycleMenuItems
        sections: root._sections

        onBackRequested: root.backRequested()
        onEditRequested: root.actionRequested("edit")
        onMenuActionTriggered: function(id) { root.actionRequested(id) }
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
            visible: root._showSectionToolbar
            height: visible ? implicitHeight : 0
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
                loadingMessage: "Loading party overview..."
                sourceComponent: Component {
                    PartySections.PartyOverviewSection {
                        partyInformationFields: root._partyInformationFields
                        legalRegistrationFields: root._legalRegistrationFields
                        hasLegalRegistrationData: root._hasLegalRegistrationData
                        contactFields: root._contactFields
                        addressFields: root._addressFields
                        businessRoles: root._businessRoles
                        relatedActions: root._relatedActions
                        recentActivity: root._recentActivity

                        onNavigateToDestination: function(destinationId) {
                            root.actionRequested(destinationId)
                        }
                        onViewAllActivityRequested: {
                            const index = root._indexOfSection("Activity")
                            if (index >= 0) detailPage.scrollToSection(index)
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Activity"
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: activityLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Activity"
                keepLoaded: true
                loadingMessage: "Loading party activity..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    PartySections.PartyActivitySection {
                        width: parent ? parent.width : 0
                        height: Math.max(420, detailPage.contentViewportHeight)
                        catalog: root._activityCatalog
                        busy: root.busy
                        searchText: root._activitySearch
                        dateFilterOptions: root._activityDateFilterOptions
                        dateFilter: root._activityDateFilter

                        onRefreshRequested: root._refreshActivityPage()
                        onSearchChanged: function(text) {
                            root._activitySearch = text
                            root._activityPage = 1
                            root._refreshActivityPage()
                        }
                        onDateFilterRequested: function(value) {
                            root._activityDateFilter = value
                            root._activityPage = 1
                            root._refreshActivityPage()
                        }
                        onPageRequested: function(page) {
                            root._activityPage = page
                            root._refreshActivityPage()
                        }
                        onPageSizeRequested: function(pageSize) {
                            root._activityPageSize = pageSize
                            root._activityPage = 1
                            root._refreshActivityPage()
                        }
                    }
                }
            }
        }
    }
}
