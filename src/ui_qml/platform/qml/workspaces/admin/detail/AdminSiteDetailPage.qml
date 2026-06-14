pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import "../components"
import "../sections"

Item {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var site: ({})
    property var departmentCatalog: ({ "items": [], "emptyState": "No departments are available yet." })
    property var departmentColumns: []
    property var siteCalendarAssignment: ({})
    property var calendarSourceChain: []
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)
    signal relatedRowActivated(string sectionId, string rowId)

    readonly property var _state: (root.site && root.site.state) ? root.site.state : ({})
    readonly property string _title: String(root.site && root.site.title ? root.site.title : "Site")
    readonly property string _status: String(root.site && root.site.statusLabel ? root.site.statusLabel : "")
    readonly property string _subtitle: String(root.site && root.site.subtitle ? root.site.subtitle : "")
    readonly property string _supportingText: String(root.site && root.site.supportingText ? root.site.supportingText : "")
    readonly property string _metaText: String(root.site && root.site.metaText ? root.site.metaText : "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property bool _inventoryEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("inventory_procurement") : false
    readonly property bool _pmEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("project_management") : false
    readonly property bool _maintenanceEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("maintenance_management") : false
    readonly property string _siteId: String(root._state.siteId || root._state.id || root.site.id || "")
    readonly property bool _hasCalendarAssignment: String(root.siteCalendarAssignment && root.siteCalendarAssignment.assignmentId ? root.siteCalendarAssignment.assignmentId : "").length > 0
    readonly property var _departmentRows: {
        const rows = root.departmentCatalog.items || []
        const siteId = root._siteId
        if (siteId.length === 0) {
            return []
        }
        return rows.filter(function(row) {
            const state = row && row.state ? row.state : {}
            return String(state.siteId || "") === siteId
        })
    }
    readonly property var _sections: {
        const sections = [
            { "label": "Overview" },
            { "label": "Departments", "count": root._departmentRows.length }
        ]
        if (root._maintenanceEnabled) {
            sections.push({ "label": "Structures" })
        }
        if (root._inventoryEnabled) {
            sections.push({ "label": "Warehouses" })
        }
        if (root._pmEnabled) {
            sections.push({ "label": "Projects" })
        }
        if (root._maintenanceEnabled) {
            sections.push({ "label": "Assets" })
        }
        sections.push({ "label": "Calendar" })
        sections.push({ "label": "Documents" })
        sections.push({ "label": "Audit" })
        return sections
    }
    readonly property string _activeSectionLabel: {
        const section = root._sections[root.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property string _toolbarSubtitle: {
        switch (root._activeSectionLabel) {
        case "Overview":
            return root._subtitle
        case "Departments":
            return "Shared departments mapped to this site through the platform department master."
        case "Structures":
            return "Maintenance-owned location and structure hierarchy delegated from the shared site master."
        case "Warehouses":
            return "Inventory & Procurement warehouse alignment delegated from the shared site master."
        case "Projects":
            return "Project Management project/site alignment delegated to the PM module."
        case "Assets":
            return "Maintenance-owned asset and location alignment delegated from the shared site master."
        case "Calendar":
            return "Site-level calendar assignment and working schedule inherited from the global calendar hierarchy."
        case "Documents":
            return "Site-scoped document governance stays in the shared document workspace."
        case "Audit":
            return "Entity-level audit detail is still routed through the shared audit workspace."
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
        if (root._activeSectionLabel === "Departments") {
            return [
                { "id": "create_department", "label": "New Department", "icon": "add" },
                { "id": "show_departments", "label": "Open Departments", "icon": "chevron_right" }
            ]
        }
        if (root._activeSectionLabel === "Calendar") {
            return [
                { "id": "assign_calendar", "label": root._hasCalendarAssignment ? "Change Calendar" : "Assign Calendar", "icon": "calendar" },
                { "id": "clear_calendar_assignment", "label": "Clear Assignment", "icon": "delete", "danger": true, "enabled": root._hasCalendarAssignment },
                { "id": "open_calendar_mgmt", "label": "Calendar Management", "icon": "chevron_right" },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Documents") {
            return [
                { "id": "show_documents", "label": "Open Documents", "icon": "chevron_right" }
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
        { "label": "Site Code", "value": root._state.siteCode },
        { "label": "Display Name", "value": root._state.name || root.site.title },
        { "label": "Site Type", "value": root._state.siteType },
        { "label": "Status", "value": root._status },
        { "label": "Version", "value": root._state.version },
        { "label": "Active", "value": root._isActive },
        { "label": "City", "value": root._state.city },
        { "label": "Country", "value": root._state.country },
        { "label": "Timezone", "value": root._state.timezoneName },
        { "label": "Currency", "value": root._state.currencyCode }
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
                loadingMessage: "Loading site overview..."
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
                                    title: "Site Summary"
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
                                    implicitHeight: notesColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Operational Notes"
                                    outlined: true

                                    ColumnLayout {
                                        id: notesColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        AppWidgets.StatusChip {
                                            visible: root._status.length > 0
                                            status: root._status
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            visible: root._supportingText.length > 0
                                            text: root._supportingText
                                            color: Theme.AppTheme.textSecondary
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            visible: root._metaText.length > 0
                                            text: root._metaText
                                            color: Theme.AppTheme.textMuted
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: String(root._state.description || root._state.notes || "This shared platform site anchors downstream PM, maintenance, and inventory records without duplicating those module-owned operational structures here.")
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
            implicitHeight: root._activeSectionLabel === "Departments" ? departmentsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: departmentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Departments"
                keepLoaded: true
                loadingMessage: "Loading site departments..."
                sourceComponent: Component {
                    AdminDetailTableSection {
                        sectionLabel: "Departments"
                        infoMessage: "Departments remain shared platform masters. This section filters them by the selected site association."
                        emptyTitle: "No departments for this site"
                        emptyMessage: "No departments are currently assigned to this site."
                        rows: root._departmentRows
                        columns: root.departmentColumns
                        tableHeight: root._tableHeightForCount(root._departmentRows.length)
                        loading: root.busy
                        onRowActivated: function(rowId) {
                            root.relatedRowActivated("departments", rowId)
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Structures" ? structuresLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: structuresLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Structures"
                keepLoaded: true
                loadingMessage: "Loading site structures..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Structures"
                        infoMessage: "Maintenance is enabled for this tenant. Physical locations, structures, and systems stay maintenance-owned and are not duplicated in Platform admin."
                        cardTitle: "Maintenance Boundary"
                        notes: [
                            "Use the Maintenance module to manage location hierarchies, structures, and systems anchored to this site.",
                            "Platform admin keeps the shared site master authoritative while maintenance owns the operational asset geography below it."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Warehouses" ? warehousesLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: warehousesLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Warehouses"
                keepLoaded: true
                loadingMessage: "Loading site warehouse guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Warehouses"
                        infoMessage: "Inventory & Procurement is enabled for this tenant. Warehouse master data stays module-owned and links back to the shared site master."
                        cardTitle: "Inventory Boundary"
                        notes: [
                            "Use Inventory & Procurement workspaces to manage warehouses, zones, bins, and stock posture anchored to this site.",
                            "Platform admin will surface site-to-warehouse relationships here once the cross-module integration contract is promoted into the admin controller layer."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Projects" ? projectsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: projectsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Projects"
                keepLoaded: true
                loadingMessage: "Loading site project guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Projects"
                        infoMessage: "Project Management is enabled for this tenant. Project/site alignment stays PM-owned and references the shared site master."
                        cardTitle: "PM Boundary"
                        notes: [
                            "Use the Project Management module to review projects, work packages, schedules, and delivery records linked to this site.",
                            "Platform admin keeps the site reference authoritative while PM owns the project and task execution layer."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Assets" ? assetsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: assetsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Assets"
                keepLoaded: true
                loadingMessage: "Loading site asset guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Assets"
                        infoMessage: "Maintenance is enabled for this tenant. Asset libraries, systems, and operational equipment stay maintenance-owned and reference the shared site master."
                        cardTitle: "Asset Boundary"
                        notes: [
                            "Use the Maintenance module to manage asset libraries and operational equipment assigned to this site.",
                            "Platform admin keeps the site and organization master record stable while maintenance owns asset execution detail."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Calendar" ? calendarLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: calendarLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Calendar"
                keepLoaded: true
                loadingMessage: "Loading site calendar..."
                sourceComponent: Component {
                    AdminCalendarAssignmentSection {
                        width: parent ? parent.width : 0
                        entityType: "site"
                        entityId: root._siteId
                        entityLabel: root._title
                        assignedCalendar: root.siteCalendarAssignment
                        sourceChain: root.calendarSourceChain
                        busy: root.busy
                        onAssignCalendarRequested: root.actionRequested("assign_calendar")
                        onOpenCalendarManagementRequested: root.actionRequested("open_calendar_mgmt")
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Documents" ? documentsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: documentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Documents"
                keepLoaded: true
                loadingMessage: "Loading site document guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Documents"
                        infoMessage: "Site-scoped document governance remains in the shared documents workspace."
                        cardTitle: "Document Boundary"
                        notes: [
                            "Use the shared Documents workspace to manage governed documents and document structures linked to platform records.",
                            "The admin controller does not yet surface a site-filtered document relationship view, so this section intentionally delegates to the owning document workspace."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Audit" ? auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Audit"
                keepLoaded: true
                loadingMessage: "Loading audit guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Audit"
                        infoMessage: "Entity-level site audit detail is still routed through the shared Platform audit workspace."
                        cardTitle: "Audit Follow-up"
                        notes: [
                            "Use the shared audit workspace to inspect platform-wide events, approval history, and related operational activity for this site.",
                            "This keeps audit delivery centralized while the site detail page stays focused on master-data inspection."
                        ]
                    }
                }
            }
        }
    }
}
