pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

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

    readonly property var _orgState: (detailRoot.organization && detailRoot.organization.state)
        ? detailRoot.organization.state
        : ({})
    readonly property string _orgId: String(detailRoot.organization && detailRoot.organization.id
        ? detailRoot.organization.id
        : (detailRoot._orgState.organizationId || ""))
    readonly property string _orgTitle: String(detailRoot.organization && detailRoot.organization.title
        ? detailRoot.organization.title
        : "Organization")
    readonly property string _orgStatus: String(detailRoot.organization && detailRoot.organization.statusLabel
        ? detailRoot.organization.statusLabel
        : "")
    readonly property string _orgSubtitle: String(detailRoot.organization && detailRoot.organization.subtitle
        ? detailRoot.organization.subtitle
        : "")
    readonly property bool _isEnabledOrganization: detailRoot._orgState.isEnabled === true
    readonly property string _orgStatusTone: detailRoot._isEnabledOrganization ? "success" : "neutral"

    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Sites" },
        { "label": "Departments" },
        { "label": "Employees" },
        { "label": "Documents" },
        { "label": "Audit" }
    ]
    readonly property string _activeSectionLabel: {
        const section = detailRoot._sections[detailRoot.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property string _toolbarSubtitle: detailRoot._activeSectionLabel === "Overview"
        ? detailRoot._orgSubtitle
        : ""
    readonly property var _toolbarActions: {
        if (detailRoot._activeSectionLabel !== "Overview") {
            return [{ "id": "refresh", "label": "Refresh", "icon": "refresh" }]
        }
        const actions = [{ "id": "edit", "label": "Edit", "icon": "edit", "enabled": detailRoot.canWrite }]
        if (!detailRoot._isEnabledOrganization) {
            actions.push({ "id": "enable", "label": "Enable", "icon": "approve", "enabled": detailRoot.canWrite })
        }
        actions.push({ "id": "refresh", "label": "Refresh", "icon": "refresh" })
        return actions
    }
    // Blank persisted values ("") display as "-" rather than an empty label
    // or literal "None"/"null" -- the persisted value itself is untouched.
    function _displayValue(value) {
        const text = String(value || "").trim()
        return text.length > 0 ? text : "—"
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
    property var _auditActivity: []
    property bool _auditLoaded: false

    function _reloadDetailContext() {
        if (!detailRoot.workspaceController || detailRoot._orgId.length === 0) {
            return
        }
        detailRoot._detailContext = detailRoot.workspaceController.organizationDetailContext(detailRoot._orgId)
    }

    function _ensureAuditLoaded() {
        if (detailRoot._auditLoaded || !detailRoot.workspaceController || detailRoot._orgId.length === 0) {
            return
        }
        detailRoot._auditActivity = detailRoot.workspaceController.organizationAuditActivity(detailRoot._orgId)
        detailRoot._auditLoaded = true
    }

    onOrganizationChanged: {
        detailRoot._auditLoaded = false
        detailRoot._reloadDetailContext()
    }
    onActiveSectionIndexChanged: {
        if (detailRoot._activeSectionLabel === "Audit") {
            detailRoot._ensureAuditLoaded()
        }
    }
    Component.onCompleted: detailRoot._reloadDetailContext()

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
    readonly property var _orgSites: detailRoot.workspaceController
        ? detailRoot._filteredByOrg(detailRoot.workspaceController.sites) : []
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
        breadcrumb: detailRoot.breadcrumb
        isBusy: detailRoot.busy
        showEdit: false
        showDelete: false
        sections: detailRoot._sections

        onBackRequested: detailRoot.backRequested()
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
            detailPagePinned: true
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

        // -- Sites / Departments / Employees / Documents: real filtered lists
        Item {
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 1 ? sitesLoader.implicitHeight : 0
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
                fallbackLoadingHeight: 320
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0
                        AppWidgets.DataTable {
                            width: parent.width
                            height: 320
                            columns: detailRoot._simpleColumns
                            rows: detailRoot._orgSites
                            emptyText: "No sites recorded for this organization yet."
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

        // -- Audit: real organization-scoped audit trail -------------------
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
                loadingMessage: "Loading audit trail..."
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
                                    items: detailRoot._auditActivity
                                    emptyText: "No audit entries recorded for this organization yet."
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
