pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Models 1.0 as AppModels
import Platform.Components 1.0 as PlatformComponents
import workspaces.sites 1.0 as SitesWorkspace

Item {
    id: detailRoot

    property var organization: ({})
    property var workspaceController: null
    property var platformCatalog: null
    property var breadcrumb: []
    property bool canWrite: true
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)
    signal navigateToDestination(string destinationId)

    // Any site mutation anywhere (e.g. the "+ New Site" dialog, owned by
    // the parent OrganizationsWorkspacePage's shared dialog host) re-fetches
    // this tab's own organization-scoped page -- the same reactivity the
    // old client-side-filtered tab had via a computed property, just
    // sourced from the new paginated query instead of an in-memory list.
    Connections {
        target: detailRoot.workspaceController
        function onSitesChanged() { detailRoot._refreshSites() }
    }

    readonly property var _orgState: (detailRoot.organization && detailRoot.organization.state)
        ? detailRoot.organization.state
        : ({})
    readonly property string _orgId: String(detailRoot.organization && detailRoot.organization.id
        ? detailRoot.organization.id
        : (detailRoot._orgState.organizationId || ""))
    readonly property string _orgTitle: String(detailRoot.organization && detailRoot.organization.title
        ? detailRoot.organization.title
        : "Organization")
    readonly property var _orgStatusLabelValue: detailRoot.organization ? detailRoot.organization.statusLabel : null
    readonly property string _orgStatus: (detailRoot._orgStatusLabelValue && typeof detailRoot._orgStatusLabelValue === "object")
        ? String(detailRoot._orgStatusLabelValue.label || "")
        : String(detailRoot._orgStatusLabelValue || "")
    readonly property string _orgStatusTone: (detailRoot._orgStatusLabelValue && typeof detailRoot._orgStatusLabelValue === "object")
        ? String(detailRoot._orgStatusLabelValue.tone || "neutral")
        : "neutral"
    readonly property string _orgSubtitle: String(detailRoot.organization && detailRoot.organization.subtitle
        ? detailRoot.organization.subtitle
        : "")
    readonly property string _orgCode: String(detailRoot._orgState.organizationCode || "")
    readonly property string _orgLocation: String(detailRoot._orgState.location || detailRoot._orgState.countryName || "")
    readonly property string _headerSubtitle: detailRoot._joinNonEmpty([detailRoot._orgCode, detailRoot._orgLocation], "  ·  ")
    readonly property bool _isActiveOrganization: detailRoot._orgState.status === "active"
    readonly property bool _isInactiveOrganization: detailRoot._orgState.status === "inactive"
    readonly property bool _isArchivedOrganization: detailRoot._orgState.status === "archived"

    // -- Actions -- a standalone [Edit] button plus a lifecycle "Actions ▾"
    // menu. The menu also repeats Edit organization ahead of a divider (per
    // the approved reference header design) so every command reachable from
    // this header is keyboard/menu-discoverable, not only the quick button.
    // Archived is a terminal state (see OrganizationService._require_valid_
    // organization_transition) -- no lifecycle items apply, so the whole
    // menu is omitted rather than shown with nothing useful in it.
    readonly property var _lifecycleMenuItems: {
        const items = [
            { "id": "edit", "label": "Edit organization", "icon": "edit", "enabled": detailRoot.canWrite },
            { "separator": true }
        ]
        if (detailRoot._isActiveOrganization) {
            items.push({ "id": "deactivate", "label": "Deactivate organization", "icon": "reject", "enabled": detailRoot.canWrite })
            items.push({ "id": "archive", "label": "Archive organization", "icon": "inventory", "danger": true, "enabled": detailRoot.canWrite })
        } else if (detailRoot._isInactiveOrganization) {
            items.push({ "id": "activate", "label": "Activate organization", "icon": "approve", "enabled": detailRoot.canWrite })
            items.push({ "id": "archive", "label": "Archive organization", "icon": "inventory", "danger": true, "enabled": detailRoot.canWrite })
        }
        return items
    }
    readonly property bool _showLifecycleMenu: detailRoot._isActiveOrganization || detailRoot._isInactiveOrganization

    property var _pendingConfirm: null

    function _requestLifecycleConfirm(action) {
        const name = detailRoot._orgTitle || "this organization"
        if (action === "deactivate") {
            detailRoot._pendingConfirm = {
                "action": "deactivate",
                "message": "Deactivate " + name + "?",
                "supportingText": name + " will no longer be available for new operational activity. " +
                    "Existing records and historical information will remain available according to permissions. " +
                    "If this organization is currently selected, the active organization context will be cleared."
            }
        } else if (action === "archive") {
            detailRoot._pendingConfirm = {
                "action": "archive",
                "message": "Archive " + name + "?",
                "supportingText": name + " will be removed from normal operational use and retained for historical " +
                    "reference. This action cannot be reversed through the normal Organization workspace. " +
                    "Existing business history will be preserved."
            }
        } else {
            return
        }
        _lifecycleConfirmDialog.open()
    }

    function _onLifecycleMenuAction(actionId) {
        if (actionId === "edit") {
            detailRoot.actionRequested("edit")
        } else if (actionId === "activate") {
            if (detailRoot.workspaceController) detailRoot.workspaceController.activateOrganization(detailRoot._orgId)
        } else if (actionId === "deactivate") {
            detailRoot._requestLifecycleConfirm("deactivate")
        } else if (actionId === "archive") {
            detailRoot._requestLifecycleConfirm("archive")
        }
    }

    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Sites" },
        { "label": "Departments" },
        { "label": "Employees" },
        { "label": "Documents" },
        { "label": "Activity" }
    ]
    readonly property string _activeSectionLabel: {
        const section = detailRoot._sections[detailRoot.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property string _toolbarSubtitle: {
        if (detailRoot._activeSectionLabel === "Overview") return detailRoot._orgSubtitle
        // Activity here is this organization's own history only -- distinct
        // from the tenant-wide Platform audit trail (Platform > Control).
        if (detailRoot._activeSectionLabel === "Activity") return "Activity for this organization only"
        return ""
    }
    // Identity, lifecycle badge, and Edit/Actions live in the persistent
    // header below (visible across every section) -- this per-section
    // toolbar only ever offers Refresh now.
    readonly property var _toolbarActions: [{ "id": "refresh", "label": "Refresh", "icon": "refresh" }]
    // Blank persisted values ("") display as "-" rather than an empty label
    // or literal "None"/"null" -- the persisted value itself is untouched.
    function _displayValue(value) {
        const text = String(value || "").trim()
        return text.length > 0 ? text : "—"
    }
    function _joinNonEmpty(parts, sep) {
        return parts.filter(function(p) { return String(p || "").trim().length > 0 }).join(sep)
    }
    readonly property string _countryDisplay: {
        const code = String(detailRoot._orgState.countryCode || "").trim()
        if (code.length === 0) return ""
        const options = (detailRoot.workspaceController && detailRoot.workspaceController.organizationEditorOptions)
            ? (detailRoot.workspaceController.organizationEditorOptions.countryOptions || [])
            : []
        for (let i = 0; i < options.length; i += 1) {
            if (options[i].value === code) {
                return String(options[i].label || "") + " (" + code + ")"
            }
        }
        return code
    }

    readonly property var _basicInfoFields: [
        { "label": "Organization Name", "value": detailRoot._displayValue(detailRoot._orgState.displayName || detailRoot._orgTitle) },
        { "label": "Legal Name", "value": detailRoot._displayValue(detailRoot._orgState.legalName) },
        { "label": "Code", "value": detailRoot._displayValue(detailRoot._orgState.organizationCode) },
        { "label": "Registration Number", "value": detailRoot._displayValue(detailRoot._orgState.registrationNumber) },
        { "label": "Tax / VAT ID", "value": detailRoot._displayValue(detailRoot._orgState.taxId) },
        { "label": "Status", "value": detailRoot._orgStatus.length > 0 ? detailRoot._orgStatus : "Unknown" },
        { "label": "Time Zone", "value": detailRoot._displayValue(detailRoot._orgState.timezoneName) },
        { "label": "Base Currency", "value": detailRoot._displayValue(detailRoot._orgState.baseCurrency) }
    ]
    readonly property var _addressFields: [
        { "label": "Address Line 1", "value": detailRoot._displayValue(detailRoot._orgState.addressLine1) },
        { "label": "Address Line 2", "value": detailRoot._displayValue(detailRoot._orgState.addressLine2) },
        { "label": "Postal Code", "value": detailRoot._displayValue(detailRoot._orgState.postalCode) },
        { "label": "City", "value": detailRoot._displayValue(detailRoot._orgState.city) },
        { "label": "State / Region", "value": detailRoot._displayValue(detailRoot._orgState.stateRegion) },
        { "label": "Country", "value": detailRoot._countryDisplay.length > 0 ? detailRoot._countryDisplay : "—" }
    ]
    readonly property var _contactFields: [
        { "label": "Email", "value": detailRoot._displayValue(detailRoot._orgState.email) },
        { "label": "Phone", "value": detailRoot._displayValue(detailRoot._orgState.phone) },
        { "label": "Website", "value": detailRoot._displayValue(detailRoot._orgState.website) }
    ]

    // -- Real composed detail context (statistics + recent activity) -----
    // Fetched once per organization id, not per section activation, since
    // it backs Overview which is always the first section shown.
    property var _detailContext: ({ "statistics": ({}), "recentActivity": [] })
    property var _recentActivity: []
    property bool _recentActivityLoaded: false

    function _reloadDetailContext() {
        if (!detailRoot.workspaceController || detailRoot._orgId.length === 0) {
            return
        }
        detailRoot._detailContext = detailRoot.workspaceController.organizationDetailContext(detailRoot._orgId)
    }

    function _ensureRecentActivityLoaded() {
        if (detailRoot._recentActivityLoaded || !detailRoot.workspaceController || detailRoot._orgId.length === 0) {
            return
        }
        detailRoot._recentActivity = detailRoot.workspaceController.organizationActivity(detailRoot._orgId)
        detailRoot._recentActivityLoaded = true
    }

    onOrganizationChanged: {
        detailRoot._recentActivityLoaded = false
        detailRoot._reloadDetailContext()
    }
    onActiveSectionIndexChanged: {
        if (detailRoot._activeSectionLabel === "Activity") {
            detailRoot._ensureRecentActivityLoaded()
        }
        if (detailRoot._activeSectionLabel === "Sites") {
            detailRoot._refreshSites()
        }
    }
    Component.onCompleted: {
        detailRoot._reloadDetailContext()
        detailRoot._refreshSites()
    }

    readonly property var _statistics: detailRoot._detailContext.statistics || ({})

    // -- Related Actions: real destinations only, gated by the same
    // Context Navigation Tree accessibility the sidebar itself uses. -----
    function _isDestinationAccessible(destinationId) {
        const groups = (detailRoot.platformCatalog && detailRoot.platformCatalog.contextNavigation) || []
        for (let g = 0; g < groups.length; g += 1) {
            const items = groups[g].items || []
            for (let i = 0; i < items.length; i += 1) {
                if (items[i].id === destinationId) {
                    return true
                }
            }
        }
        return false
    }
    readonly property var _relatedActions: {
        const candidates = [
            { "id": "sites", "label": "Manage Sites", "icon": "site" },
            { "id": "departments", "label": "Manage Departments", "icon": "department" },
            { "id": "employees", "label": "Manage Employees", "icon": "employee" },
            { "id": "documents", "label": "View Documents", "icon": "documents" }
        ]
        return candidates.filter(function(action) { return detailRoot._isDestinationAccessible(action.id) })
    }

    // -- Per-organization filtered catalogs (existing tenant-scoped lists,
    // filtered client-side by organizationId; a genuine per-organization
    // backend read is future work -- see Phase J report). -----------------
    function _filteredByOrg(catalog) {
        if (!catalog) return []
        const items = catalog.items || []
        const result = []
        for (let i = 0; i < items.length; i += 1) {
            const state = items[i].state || {}
            if (String(state.organizationId || "") === detailRoot._orgId) {
                result.push(items[i])
            }
        }
        return result
    }
    // -- Sites tab: a real, tenant-scoped + paginated Organization-Detail-
    // owned query (SiteService.list_sites_page_for_organization) -- unlike
    // Departments/Employees/Documents below, NOT a client-side filter of
    // the global, session-active-organization-only catalog. Works
    // correctly regardless of which organization is active in the
    // caller's session, and remains readable for inactive/archived
    // organizations (see Phase K report). ---------------------------------
    property int _sitesPage: 1
    property int _sitesPageSize: 25
    property string _sitesSearch: ""
    property string _sitesStatusFilter: ""
    property var _sitesCatalog: ({
        "title": "Sites", "subtitle": "", "emptyState": "", "items": [],
        "paginated": true, "page": 1, "pageSize": 25, "totalCount": 0, "filteredTotal": 0
    })
    property string _sitesSelectedRowId: ""
    property bool _sitesDetailOpen: false
    readonly property var _sitesStatusFilterOptions: [
        { "value": "", "label": "All" },
        { "value": "active", "label": "Active" },
        { "value": "inactive", "label": "Inactive" }
    ]
    readonly property var _sitesColumns: [
        { "key": "title", "label": "Site", "flex": 3, "minWidth": 160, "sortable": true, "required": true, "visible": true },
        { "key": "siteCode", "label": "Code", "flex": 1, "minWidth": 110, "visible": true },
        { "key": "location", "label": "Location", "flex": 2, "minWidth": 150, "visible": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 90, "type": "status", "required": true, "visible": true },
        { "key": "country", "label": "Country", "flex": 1, "minWidth": 120, "visible": false },
        { "key": "timezoneName", "label": "Time Zone", "flex": 1, "minWidth": 130, "visible": false },
        { "key": "createdAt", "label": "Created", "flex": 1, "minWidth": 140, "visible": false },
        { "key": "updatedAt", "label": "Updated", "flex": 1, "minWidth": 140, "visible": false }
    ]
    // Only your own currently-active organization can receive new sites
    // today (SiteService.create_site() -- an existing, unchanged domain
    // rule; this read-only phase does not add an explicit-organization
    // create path). Viewing another organization's sites stays fully
    // supported; creating into it from here does not.
    readonly property bool _isViewingActiveOrganization: detailRoot.platformCatalog
        && detailRoot.platformCatalog.organizationSwitcher
        && detailRoot.platformCatalog.organizationSwitcher.activeOrganizationId === detailRoot._orgId
    readonly property bool _canCreateSite: detailRoot.canWrite && detailRoot._isViewingActiveOrganization

    function _refreshSites() {
        if (!detailRoot.workspaceController || detailRoot._orgId.length === 0) return
        detailRoot._sitesCatalog = detailRoot.workspaceController.organizationSitesPage(
            detailRoot._orgId, detailRoot._sitesPage, detailRoot._sitesPageSize,
            detailRoot._sitesSearch, detailRoot._sitesStatusFilter
        )
    }
    function _openSiteDetail(siteId) {
        detailRoot._sitesSelectedRowId = siteId
        detailRoot._sitesDetailOpen = true
    }
    function _closeSiteDetail() {
        detailRoot._sitesDetailOpen = false
    }
    readonly property var _selectedSite: {
        const id = detailRoot._sitesSelectedRowId
        if (!id) return null
        const items = detailRoot._sitesCatalog.items || []
        for (let i = 0; i < items.length; i += 1) {
            if (String(items[i].id) === String(id)) return items[i]
        }
        return null
    }
    readonly property var _orgDepartments: detailRoot.workspaceController
        ? detailRoot._filteredByOrg(detailRoot.workspaceController.departments) : []
    readonly property var _orgEmployees: detailRoot.workspaceController
        ? detailRoot._filteredByOrg(detailRoot.workspaceController.employees) : []
    readonly property var _orgDocuments: detailRoot.workspaceController
        ? detailRoot._filteredByOrg(detailRoot.workspaceController.documents) : []

    readonly property var _simpleColumns: [
        { key: "title", label: "Name", flex: 2, minWidth: 160, sortable: true, visible: true },
        { key: "subtitle", label: "Details", flex: 2, minWidth: 160, sortable: false, visible: true },
        { key: "statusLabel", label: "Status", flex: 0, minWidth: 90, sortable: false, visible: true, type: "status" }
    ]

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: detailRoot._orgTitle
        statusLabel: detailRoot._orgStatus
        statusTone: detailRoot._orgStatusTone
        subtitleLine: detailRoot._headerSubtitle
        breadcrumb: detailRoot.breadcrumb
        isBusy: detailRoot.busy
        showEdit: detailRoot.canWrite
        showDelete: false
        menuActions: detailRoot._showLifecycleMenu ? detailRoot._lifecycleMenuItems : []
        sections: detailRoot._sections

        onBackRequested: detailRoot.backRequested()
        onEditRequested: detailRoot.actionRequested("edit")
        onMenuActionTriggered: function(id) { detailRoot._onLifecycleMenuAction(id) }
        onSectionChanged: function(index) {
            detailRoot.activeSectionIndex = index
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : detailRoot.width
            requestedVisible: detailRoot.errorMessage.length > 0
            tone: "danger"
            message: detailRoot.errorMessage
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : detailRoot.width
            requestedVisible: detailRoot.feedbackMessage.length > 0 && detailRoot.errorMessage.length === 0
            tone: "success"
            message: detailRoot.feedbackMessage
        }

        AppWidgets.ContextualActionToolbar {
            id: _sectionToolbar
            detailPagePinned: true
            // Sites already has its own full header (title + count) and
            // toolbar (search/filter/Columns/Refresh/+New Site) via
            // AdminEntityWorkspace below -- showing this generic per-
            // section toolbar too would duplicate both the "Sites" heading
            // and the Refresh button. `visible: false` alone leaves a blank
            // gap: the sticky header area sizes itself from `childrenRect`,
            // which (unlike a Column's own layout pass) does NOT exclude
            // invisible children -- the height must be collapsed explicitly.
            visible: detailRoot._activeSectionLabel !== "Sites"
            height: visible ? implicitHeight : 0
            width: parent ? parent.width : detailRoot.width
            title: detailRoot._activeSectionLabel
            subtitle: detailRoot._toolbarSubtitle
            busy: detailRoot.busy
            actions: detailRoot._toolbarActions
            onActionTriggered: function(actionId) {
                detailRoot.actionRequested(actionId)
            }
        }

        // -- Overview: two-region layout (main + summary rail) ------------
        Item {
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 0 ? overviewLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: overviewLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 0
                keepLoaded: true
                loadingMessage: "Loading organization overview..."
                sourceComponent: Component {
                    Column {
                        id: overviewRoot
                        width: parent ? parent.width : 0
                        spacing: 0

                        Item {
                            width: overviewRoot.width
                            implicitHeight: overviewGrid.implicitHeight + Theme.AppTheme.spacingMd * 2

                            GridLayout {
                                id: overviewGrid
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.margins: Theme.AppTheme.spacingMd
                                // overviewRoot.width is the section CONTENT column, already net
                                // of the shell/platform/detail-page nav rails -- not the window
                                // width. 640 keeps both 1600x1000 and 1366x768 desktop breakpoints
                                // two-column while a ~1000px window (content ~290px) still stacks.
                                columns: overviewRoot.width < 640 ? 1 : 2
                                columnSpacing: Theme.AppTheme.spacingMd
                                rowSpacing: Theme.AppTheme.spacingMd

                                // -- Main column: Basic Information / Registered Address / Contact
                                // ~2/3 width on desktop; content-driven height only -- never a
                                // fixed/computed override that can under-report a card's real
                                // height and get clipped by SectionCard's own clip: true.
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: overviewGrid.columns === 2
                                        ? Math.round(overviewGrid.width * 0.66)
                                        : overviewGrid.width
                                    Layout.alignment: Qt.AlignTop
                                    spacing: Theme.AppTheme.spacingMd

                                    AppWidgets.SectionCard {
                                        Layout.fillWidth: true
                                        title: "Basic Information"
                                        outlined: true

                                        GridLayout {
                                            id: basicInfoGrid
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: Theme.AppTheme.marginMd
                                            columns: 2
                                            columnSpacing: Theme.AppTheme.spacingLg
                                            rowSpacing: Theme.AppTheme.spacingSm

                                            Repeater {
                                                model: detailRoot._basicInfoFields

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
                                                        text: String(modelData.value || "—")
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
                                        title: "Registered Address"
                                        outlined: true

                                        GridLayout {
                                            id: addressGrid
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: Theme.AppTheme.marginMd
                                            columns: 2
                                            columnSpacing: Theme.AppTheme.spacingLg
                                            rowSpacing: Theme.AppTheme.spacingSm

                                            Repeater {
                                                model: detailRoot._addressFields

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
                                                        text: String(modelData.value || "—")
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
                                        title: "Contact Information"
                                        outlined: true

                                        GridLayout {
                                            id: contactGrid
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: Theme.AppTheme.marginMd
                                            columns: 2
                                            columnSpacing: Theme.AppTheme.spacingLg
                                            rowSpacing: Theme.AppTheme.spacingSm

                                            Repeater {
                                                model: detailRoot._contactFields

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
                                                        text: String(modelData.value || "—")
                                                        color: Theme.AppTheme.textPrimary
                                                        font.pixelSize: Theme.AppTheme.smallSize
                                                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                // -- Summary rail: statistics + activity + actions (~1/3 width)
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: overviewGrid.columns === 2
                                        ? overviewGrid.width - Math.round(overviewGrid.width * 0.66) - overviewGrid.columnSpacing
                                        : overviewGrid.width
                                    Layout.alignment: Qt.AlignTop
                                    spacing: Theme.AppTheme.spacingMd

                                    AppWidgets.SectionCard {
                                        Layout.fillWidth: true
                                        title: "Key Statistics"
                                        outlined: true

                                        GridLayout {
                                            id: statsGrid
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: Theme.AppTheme.marginMd
                                            columns: 2
                                            columnSpacing: Theme.AppTheme.spacingSm
                                            rowSpacing: Theme.AppTheme.spacingSm

                                            AppWidgets.OverviewMetricTile {
                                                Layout.fillWidth: true
                                                compact: true
                                                label: "Sites"
                                                value: String(detailRoot._statistics.siteCount !== undefined ? detailRoot._statistics.siteCount : "--")
                                                clickable: detailRoot._isDestinationAccessible("sites")
                                                onActivated: detailRoot.navigateToDestination("sites")
                                            }
                                            AppWidgets.OverviewMetricTile {
                                                Layout.fillWidth: true
                                                compact: true
                                                label: "Departments"
                                                value: String(detailRoot._statistics.departmentCount !== undefined ? detailRoot._statistics.departmentCount : "--")
                                                clickable: detailRoot._isDestinationAccessible("departments")
                                                onActivated: detailRoot.navigateToDestination("departments")
                                            }
                                            AppWidgets.OverviewMetricTile {
                                                Layout.fillWidth: true
                                                compact: true
                                                label: "Employees"
                                                value: String(detailRoot._statistics.employeeCount !== undefined ? detailRoot._statistics.employeeCount : "--")
                                                clickable: detailRoot._isDestinationAccessible("employees")
                                                onActivated: detailRoot.navigateToDestination("employees")
                                            }
                                            AppWidgets.OverviewMetricTile {
                                                Layout.fillWidth: true
                                                compact: true
                                                label: "Documents"
                                                value: String(detailRoot._statistics.documentCount !== undefined ? detailRoot._statistics.documentCount : "--")
                                                clickable: detailRoot._isDestinationAccessible("documents")
                                                onActivated: detailRoot.navigateToDestination("documents")
                                            }
                                        }
                                    }

                                    AppWidgets.SectionCard {
                                        Layout.fillWidth: true
                                        title: "Recent Activity"
                                        outlined: true

                                        ColumnLayout {
                                            id: activityColumn
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: Theme.AppTheme.marginMd
                                            spacing: Theme.AppTheme.spacingSm

                                            AppControls.Label {
                                                Layout.alignment: Qt.AlignRight
                                                visible: (detailRoot._detailContext.recentActivity || []).length > 0
                                                text: "View all"
                                                color: Theme.AppTheme.accent
                                                font.pixelSize: Theme.AppTheme.smallSize
                                                font.bold: true

                                                HoverHandler { cursorShape: Qt.PointingHandCursor }
                                                // scrollToSection (not a direct activeSectionIndex
                                                // assignment) so the nav rail's own highlighted
                                                // item stays in sync -- it owns that state and only
                                                // updates it through this call or a rail click.
                                                TapHandler { onTapped: detailPage.scrollToSection(5) }
                                            }

                                            AppWidgets.ActivityFeed {
                                                Layout.fillWidth: true
                                                items: detailRoot._detailContext.recentActivity || []
                                                emptyText: "No recent administrative activity for this organization."
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // -- Related Actions: full content width (not confined to the
                        // ~1/3 summary rail) so its tiles get real room to lay out
                        // horizontally instead of always falling back to a stack.
                        Item {
                            width: overviewRoot.width
                            implicitHeight: detailRoot._relatedActions.length > 0
                                ? relatedActionsCard.implicitHeight + Theme.AppTheme.spacingMd * 2
                                : 0
                            visible: detailRoot._relatedActions.length > 0

                            AppWidgets.SectionCard {
                                id: relatedActionsCard
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: Theme.AppTheme.spacingMd
                                title: "Related Actions"
                                outlined: true

                                GridLayout {
                                    id: actionsGrid
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: Theme.AppTheme.marginMd
                                    columnSpacing: Theme.AppTheme.spacingSm
                                    rowSpacing: Theme.AppTheme.spacingSm
                                    // Responsive tiling driven by the card's own available
                                    // width (a container query, not a window breakpoint):
                                    // one row if every tile fits at its minimum readable
                                    // width, else a 2-column wrap, else a single column.
                                    readonly property int _minTileWidth: 150
                                    readonly property int _actionCount: detailRoot._relatedActions.length
                                    columns: {
                                        if (actionsGrid._actionCount <= 1) return 1
                                        const perRow = Math.max(
                                            1,
                                            Math.floor(
                                                (actionsGrid.width + actionsGrid.columnSpacing)
                                                / (actionsGrid._minTileWidth + actionsGrid.columnSpacing)
                                            )
                                        )
                                        if (perRow >= actionsGrid._actionCount) return actionsGrid._actionCount
                                        return perRow >= 2 ? 2 : 1
                                    }

                                    Repeater {
                                        model: detailRoot._relatedActions

                                        delegate: AppWidgets.ActionTile {
                                            required property var modelData
                                            Layout.fillWidth: true

                                            label: String(modelData.label || "")
                                            iconName: String(modelData.icon || "")

                                            onActivated: detailRoot.navigateToDestination(String(modelData.id || ""))
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // -- Sites: a real Organization-scoped management workspace (a
        // tenant-scoped backend read, not a client-side filter of the
        // global session-active-organization catalog -- see Phase K
        // report). Row activation opens the same AdminSiteDetailPage the
        // standalone Sites workspace uses. --------------------------------
        Item {
            // Unlike the other (still content-height-driven) sections
            // below, Sites fills the page's actual available viewport --
            // AdminEntityWorkspace is a full-panel component (fixed
            // pagination footer pinned to ITS bottom, internal DataTable
            // scrolling), not content that should size to its own row
            // count. Binding to a fixed pixel height here previously left
            // dead space below the pagination footer on tall viewports and
            // pushed the footer out of view entirely on short ones.
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 1
                ? Math.max(420, detailPage.contentViewportHeight)
                : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: sitesLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading sites..."
                fallbackLoadingHeight: Math.max(420, detailPage.contentViewportHeight)
                sourceComponent: Component {
                    Item {
                        id: sitesSectionRoot
                        width: parent ? parent.width : 0
                        height: Math.max(420, detailPage.contentViewportHeight)

                        AppModels.DynamicTableModel {
                            id: _sitesTableModel
                            rows: detailRoot._sitesCatalog.items || []
                        }

                        PlatformComponents.AdminEntityWorkspace {
                            id: _sitesWorkspace
                            anchors.fill: parent
                            visible: !detailRoot._sitesDetailOpen
                            sectionTitle: "Sites"
                            entityLabel: "Site"
                            catalog: detailRoot._sitesCatalog
                            catalogModel: _sitesTableModel
                            tableId: "organization.detail.sites.table"
                            columns: detailRoot._sitesColumns
                            canCreate: detailRoot._canCreateSite
                            isBusy: detailRoot.busy
                            isLoading: false
                            errorMessage: detailRoot.errorMessage
                            feedbackMessage: detailRoot.feedbackMessage
                            selectedRowId: detailRoot._sitesSelectedRowId
                            showSearch: true
                            searchText: detailRoot._sitesSearch
                            pageSizeOptions: [25, 50, 100]

                            AppControls.ComboBox {
                                id: _sitesStatusFilterCombo
                                Layout.preferredWidth: 150
                                model: detailRoot._sitesStatusFilterOptions
                                textRole: "label"
                                valueRole: "value"
                                currentIndex: {
                                    const filter = detailRoot._sitesStatusFilter
                                    for (let i = 0; i < detailRoot._sitesStatusFilterOptions.length; i += 1) {
                                        if (detailRoot._sitesStatusFilterOptions[i].value === filter) return i
                                    }
                                    return 0
                                }
                                onActivated: {
                                    detailRoot._sitesStatusFilter = String(currentValue || "")
                                    detailRoot._sitesPage = 1
                                    detailRoot._refreshSites()
                                }
                            }

                            onCreateRequested: detailRoot.actionRequested("create_site")
                            onRowSelected: function(id) { detailRoot._sitesSelectedRowId = id }
                            onRowActivated: function(id) { detailRoot._openSiteDetail(id) }
                            onRefreshRequested: detailRoot._refreshSites()
                            onSearchChanged: function(text) {
                                detailRoot._sitesSearch = text
                                detailRoot._sitesPage = 1
                                detailRoot._refreshSites()
                            }
                            onPageRequested: function(page) {
                                detailRoot._sitesPage = page
                                detailRoot._refreshSites()
                            }
                            onPageSizeRequested: function(pageSize) {
                                detailRoot._sitesPageSize = pageSize
                                detailRoot._sitesPage = 1
                                detailRoot._refreshSites()
                            }
                            onClearFiltersRequested: {
                                detailRoot._sitesSearch = ""
                                detailRoot._sitesStatusFilter = ""
                                detailRoot._sitesPage = 1
                                detailRoot._refreshSites()
                            }
                        }

                        Loader {
                            anchors.fill: parent
                            active: detailRoot._sitesDetailOpen
                            visible: active
                            asynchronous: true

                            sourceComponent: Component {
                                SitesWorkspace.AdminSiteDetailPage {
                                    platformCatalog: detailRoot.platformCatalog
                                    site: detailRoot._selectedSite || ({})
                                    departmentCatalog: detailRoot.workspaceController
                                        ? detailRoot.workspaceController.departments
                                        : ({ "items": [] })
                                    employeeCatalog: detailRoot.workspaceController
                                        ? detailRoot.workspaceController.employees
                                        : ({ "items": [] })
                                    canWrite: detailRoot.canWrite
                                    busy: detailRoot.busy
                                    errorMessage: detailRoot.errorMessage
                                    feedbackMessage: detailRoot.feedbackMessage

                                    onBackRequested: detailRoot._closeSiteDetail()
                                    onActionRequested: function(actionId) {
                                        // Only the site's own lifecycle/refresh are wired
                                        // here -- cross-links to Departments/Employees/
                                        // Calendar management from within a nested Site
                                        // Detail are not yet re-routed to this
                                        // organization's own scoped tabs (see Phase K
                                        // report's known-limitations section).
                                        if (actionId === "toggle_active") {
                                            if (detailRoot.workspaceController && detailRoot._sitesSelectedRowId) {
                                                detailRoot.workspaceController.toggleSiteActive(detailRoot._sitesSelectedRowId)
                                            }
                                        } else if (actionId === "refresh") {
                                            detailRoot._refreshSites()
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
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 2 ? departmentsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: departmentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 2
                keepLoaded: true
                loadingMessage: "Loading departments..."
                fallbackLoadingHeight: 320
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0
                        AppWidgets.DataTable {
                            width: parent.width
                            height: 320
                            columns: detailRoot._simpleColumns
                            rows: detailRoot._orgDepartments
                            emptyText: "No departments recorded for this organization yet."
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 3 ? employeesLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: employeesLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 3
                keepLoaded: true
                loadingMessage: "Loading employees..."
                fallbackLoadingHeight: 320
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0
                        AppWidgets.DataTable {
                            width: parent.width
                            height: 320
                            columns: detailRoot._simpleColumns
                            rows: detailRoot._orgEmployees
                            emptyText: "No employees recorded for this organization yet."
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 4 ? documentsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: documentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 4
                keepLoaded: true
                loadingMessage: "Loading documents..."
                fallbackLoadingHeight: 320
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0
                        AppWidgets.DataTable {
                            width: parent.width
                            height: 320
                            columns: detailRoot._simpleColumns
                            rows: detailRoot._orgDocuments
                            emptyText: "No documents recorded for this organization yet."
                        }
                    }
                }
            }
        }

        // -- Activity: this organization's own history only -- a distinct,
        // narrower scope than the tenant-wide Platform audit trail (Platform
        // > Control > Audit). Same underlying entries as Overview's Recent
        // Activity preview, shown here in full (see terminology-glossary.md
        // "Recent Activity" / "Audit").
        Item {
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 5 ? auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 5
                keepLoaded: true
                loadingMessage: "Loading organization activity..."
                sourceComponent: Component {
                    Column {
                        id: auditRoot
                        width: parent ? parent.width : 0
                        spacing: 0


                        Item {
                            width: auditRoot.width
                            implicitHeight: auditColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: auditColumn
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.margins: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.ActivityFeed {
                                    Layout.fillWidth: true
                                    items: detailRoot._recentActivity
                                    emptyText: "No activity recorded for this organization yet."
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    AppControls.ConfirmationDialog {
        id: _lifecycleConfirmDialog
        title: "Confirm"
        confirmLabel: detailRoot._pendingConfirm && detailRoot._pendingConfirm.action === "archive"
            ? "Archive organization" : "Deactivate organization"
        confirmIcon: detailRoot._pendingConfirm && detailRoot._pendingConfirm.action === "archive" ? "inventory" : "reject"
        confirmDanger: true
        message: detailRoot._pendingConfirm ? String(detailRoot._pendingConfirm.message || "") : ""
        supportingText: detailRoot._pendingConfirm ? String(detailRoot._pendingConfirm.supportingText || "") : ""
        onConfirmed: {
            const pending = detailRoot._pendingConfirm
            if (!pending || !detailRoot.workspaceController) return
            if (pending.action === "deactivate") {
                detailRoot.workspaceController.deactivateOrganization(detailRoot._orgId)
            } else if (pending.action === "archive") {
                detailRoot.workspaceController.archiveOrganization(detailRoot._orgId)
            }
            detailRoot._pendingConfirm = null
        }
    }
}
