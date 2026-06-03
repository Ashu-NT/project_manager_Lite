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
    property var department: ({})
    property var employeeCatalog: ({ "items": [], "emptyState": "No employees are available yet." })
    property var employeeColumns: []
    property var deptCalendarAssignment: ({})
    property var calendarSourceChain: []
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)
    signal relatedRowActivated(string sectionId, string rowId)

    readonly property var _state: (root.department && root.department.state) ? root.department.state : ({})
    readonly property string _title: String(root.department && root.department.title ? root.department.title : "Department")
    readonly property string _status: String(root.department && root.department.statusLabel ? root.department.statusLabel : "")
    readonly property string _subtitle: String(root.department && root.department.subtitle ? root.department.subtitle : "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property bool _inventoryEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("inventory_procurement") : false
    readonly property bool _pmEnabled: root.platformCatalog ? root.platformCatalog.isModuleEnabled("project_management") : false
    readonly property string _departmentId: String(root._state.departmentId || root._state.id || root.department.id || "")
    readonly property bool _hasCalendarAssignment: String(root.deptCalendarAssignment && root.deptCalendarAssignment.assignmentId ? root.deptCalendarAssignment.assignmentId : "").length > 0
    readonly property var _employeeRows: {
        const rows = root.employeeCatalog.items || []
        const departmentId = root._departmentId
        if (departmentId.length === 0) {
            return []
        }
        return rows.filter(function(row) {
            const state = row && row.state ? row.state : {}
            return String(state.departmentId || "") === departmentId
        })
    }
    readonly property var _sections: {
        const sections = [
            { "label": "Overview" },
            { "label": "Employees", "count": root._employeeRows.length },
            { "label": "Users" }
        ]
        if (root._pmEnabled) {
            sections.push({ "label": "Projects" })
        }
        if (root._inventoryEnabled) {
            sections.push({ "label": "Warehouses" })
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
        case "Employees":
            return "Employees aligned to this department through the shared employee master."
        case "Calendar":
            return "Department-level calendar assignment and working schedule."
        case "Users":
            return "Identity accounts remain governed by the shared platform user workspace."
        case "Projects":
            return "Project ownership and staffing remain governed by the Project Management module."
        case "Warehouses":
            return "Inventory warehouse alignment remains governed by Inventory & Procurement."
        case "Documents":
            return "Department-linked document governance stays in the shared document workspace."
        case "Audit":
            return "Entity-level audit detail is routed through the shared audit workspace."
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
        if (root._activeSectionLabel === "Employees") {
            return [
                { "id": "create_employee", "label": "New Employee", "icon": "add" },
                { "id": "show_employees", "label": "Open Employees", "icon": "chevron_right" }
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
        if (root._activeSectionLabel === "Users") {
            return [
                { "id": "show_users", "label": "Open Users", "icon": "chevron_right" }
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
        { "label": "Department Code", "value": root._state.departmentCode },
        { "label": "Display Name", "value": root._state.name || root.department.title },
        { "label": "Department Type", "value": root._state.departmentType },
        { "label": "Cost Center", "value": root._state.costCenterCode },
        { "label": "Status", "value": root._status },
        { "label": "Version", "value": root._state.version },
        { "label": "Site ID", "value": root._state.siteId },
        { "label": "Default Location ID", "value": root._state.defaultLocationId },
        { "label": "Parent Department ID", "value": root._state.parentDepartmentId },
        { "label": "Active", "value": root._isActive }
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
                loadingMessage: "Loading department overview..."
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
                                    title: "Department Summary"
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

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: String(root._state.description || root._state.notes || root.department.supportingText || "Department hierarchy and site alignment stay in the shared platform master data.")
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
            implicitHeight: root.activeSectionIndex === 1 ? employeesLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: employeesLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading department employees..."
                sourceComponent: Component {
                    AdminDetailTableSection {
                        sectionLabel: "Employees"
                        infoMessage: "Employee assignment remains sourced from the shared employee master."
                        emptyTitle: "No employees mapped"
                        emptyMessage: "This department does not currently have employees assigned."
                        rows: root._employeeRows
                        columns: root.employeeColumns
                        loading: root.busy
                        tableHeight: root._tableHeightForCount(root._employeeRows.length)
                        onRowActivated: function(rowId) {
                            root.relatedRowActivated("employees", rowId)
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Users" ? usersLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: usersLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Users"
                keepLoaded: true
                loadingMessage: "Loading user access guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Users"
                        infoMessage: "Department-to-user alignment remains indirect through employee records and scoped access assignments."
                        cardTitle: "Platform Identity Boundary"
                        notes: [
                            "User accounts remain owned by the shared platform identity workspace.",
                            "Use the Users workspace for credential, role, session, and access-governance operations.",
                            "Department context should be inferred from employee and scope assignments rather than duplicated here."
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
                loadingMessage: "Loading project integration guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Projects"
                        infoMessage: "Project staffing and cost ownership stay inside the Project Management module."
                        cardTitle: "Project Management Boundary"
                        notes: [
                            "Departments should be referenced by PM resources and project metadata rather than re-managed here.",
                            "Cross-module project views should open the PM module instead of duplicating task or schedule data in Platform."
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
                loadingMessage: "Loading inventory integration guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Warehouses"
                        infoMessage: "Warehouse and stock-location ownership stays inside Inventory & Procurement."
                        cardTitle: "Inventory Boundary"
                        notes: [
                            "Department usage of warehouses should be referenced from Inventory & Procurement rather than maintained in Platform Admin.",
                            "Any linked warehouse views should remain capability-gated and open the module that owns the records."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Calendar" ? deptCalendarLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: deptCalendarLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Calendar"
                keepLoaded: true
                loadingMessage: "Loading department calendar..."
                sourceComponent: Component {
                    AdminCalendarAssignmentSection {
                        width: parent ? parent.width : 0
                        entityType: "department"
                        entityId: root._departmentId
                        entityLabel: root._title
                        assignedCalendar: root.deptCalendarAssignment
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
                loadingMessage: "Loading document guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Documents"
                        infoMessage: "Department-linked document governance stays in the shared document workspace."
                        cardTitle: "Document Governance"
                        notes: [
                            "Platform Admin should not duplicate document metadata, revisions, or permission management here.",
                            "Use the shared Documents workspace for attachment, revision, and lifecycle operations."
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
                        infoMessage: "Entity-level audit trails stay centralized in the shared audit workspace."
                        cardTitle: "Audit Boundary"
                        notes: [
                            "Use the Audit workspace for actor history, change payloads, and export workflows.",
                            "Department detail pages should link into the shared audit workflow instead of duplicating event storage."
                        ]
                    }
                }
            }
        }
    }
}
