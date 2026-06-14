pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "../components"
import "../sections"

Item {
    id: root

    property var employee: ({})
    property bool pmEnabled: false
    property var empCalendarAssignment: ({})
    property var calendarSourceChain: []
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)

    readonly property var _state: (root.employee && root.employee.state) ? root.employee.state : ({})
    readonly property string _title: String(root.employee && root.employee.title ? root.employee.title : "Employee")
    readonly property string _status: String(root.employee && root.employee.statusLabel ? root.employee.statusLabel : "")
    readonly property string _subtitle: String(root.employee && root.employee.subtitle ? root.employee.subtitle : "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property bool _hasCalendarAssignment: String(root.empCalendarAssignment && root.empCalendarAssignment.assignmentId ? root.empCalendarAssignment.assignmentId : "").length > 0
    readonly property var _sections: {
        const sections = [
            { "label": "Overview" },
            { "label": "User Account" },
            { "label": "Assignments" }
        ]
        if (root.pmEnabled) {
            sections.push({ "label": "Timesheets" })
            sections.push({ "label": "Certifications" })
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
        case "User Account":
            return "Identity accounts remain governed by the shared Users workspace."
        case "Assignments":
            return "Project assignments and staffing usage remain governed by Project Management."
        case "Timesheets":
            return "Time-entry workflows remain governed by shared timesheet and PM execution surfaces."
        case "Certifications":
            return "Skill and certification posture remains governed by Project Management resource controls."
        case "Calendar":
            return "Employee calendar assignment — governs working hours, vacation, and recurring availability."
        case "Documents":
            return "Employee-linked document governance stays in the shared document workspace."
        case "Audit":
            return "Entity-level audit detail stays in the shared audit workspace."
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
        if (root._activeSectionLabel === "User Account") {
            return [
                { "id": "show_users", "label": "Open Users", "icon": "chevron_right" }
            ]
        }
        if (root._activeSectionLabel === "Assignments" || root._activeSectionLabel === "Certifications") {
            return [
                { "id": "open_resources", "label": "Open Resources", "icon": "chevron_right" }
            ]
        }
        if (root._activeSectionLabel === "Timesheets") {
            return [
                { "id": "open_timesheets", "label": "Open Timesheets", "icon": "chevron_right" }
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
        { "label": "Employee Code", "value": root._state.employeeCode },
        { "label": "Full Name", "value": root._state.fullName || root.employee.title },
        { "label": "Job Title", "value": root._state.title },
        { "label": "Employment Type", "value": root._state.employmentType },
        { "label": "Status", "value": root._status },
        { "label": "Version", "value": root._state.version },
        { "label": "Department", "value": root._state.departmentName },
        { "label": "Site", "value": root._state.siteName },
        { "label": "Email", "value": root._state.email },
        { "label": "Phone", "value": root._state.phone }
    ]

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
            implicitHeight: root._activeSectionLabel === "Overview" ? overviewLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: overviewLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Overview"
                keepLoaded: true
                loadingMessage: "Loading employee overview..."
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
                                    title: "Employment Summary"
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
                                                        : String(modelData.value)
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
                                    title: "Platform Boundary"
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
                                            text: String(root.employee.supportingText || root.employee.metaText || "Employees remain platform-owned master records. Downstream modules should reference them through shared staffing and identity integrations.")
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
            implicitHeight: root._activeSectionLabel === "User Account" ? userLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: userLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "User Account"
                keepLoaded: true
                loadingMessage: "Loading user-account guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "User Account"
                        infoMessage: "Identity accounts remain governed by the shared Users workspace."
                        cardTitle: "Identity Boundary"
                        notes: [
                            "Use the Users workspace for credential, role, and activation governance.",
                            "Employee records should stay linked to identity and staffing workflows by reference instead of duplicating user-account state here."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Assignments" ? assignmentsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: assignmentsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Assignments"
                keepLoaded: true
                loadingMessage: "Loading assignment guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Assignments"
                        infoMessage: "Project and task assignments remain governed by the Project Management resource model."
                        cardTitle: "PM Staffing Boundary"
                        notes: [
                            "Open the Project Management Resources workspace to inspect allocations, assignments, and utilization.",
                            "Platform Admin should not duplicate PM staffing ledgers inside the employee detail page."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Timesheets" ? timesheetsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: timesheetsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Timesheets"
                keepLoaded: true
                loadingMessage: "Loading timesheet guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Timesheets"
                        infoMessage: "Time-entry workflows remain governed by PM and shared timesheet services."
                        cardTitle: "Timesheet Boundary"
                        notes: [
                            "Open the PM Timesheets workspace to review submitted hours, approvals, and task-linked labor usage.",
                            "Employee detail pages should not duplicate timesheet approval or entry-management workflows."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Certifications" ? certificationsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: certificationsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Certifications"
                keepLoaded: true
                loadingMessage: "Loading certification guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Certifications"
                        infoMessage: "Resource skills and certifications remain governed by Project Management resource controls."
                        cardTitle: "Certification Boundary"
                        notes: [
                            "Open the PM Resources workspace to manage certifications, skills, and assignment-readiness.",
                            "Platform employee records should stay focused on shared master data rather than duplicating PM qualification ledgers."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Calendar" ? empCalendarLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: empCalendarLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Calendar"
                keepLoaded: true
                loadingMessage: "Loading employee calendar..."
                sourceComponent: Component {
                    AdminCalendarAssignmentSection {
                        width: parent ? parent.width : 0
                        entityType: "employee"
                        entityId: String(root._state.employeeId || root._state.id || "")
                        entityLabel: root._title
                        assignedCalendar: root.empCalendarAssignment
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
                        infoMessage: "Employee-linked document governance stays in the shared document workspace."
                        cardTitle: "Document Governance"
                        notes: [
                            "Use the shared Documents workspace for attachment, revision, and access workflows.",
                            "Platform Admin should not duplicate document lifecycle controls in the employee detail page."
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
                        infoMessage: "Employee audit trails stay centralized in the shared audit workspace."
                        cardTitle: "Audit Boundary"
                        notes: [
                            "Use the Audit workspace for actor history, change payloads, and export workflows.",
                            "Employee detail pages should link into shared audit flows rather than duplicate audit storage."
                        ]
                    }
                }
            }
        }
    }
}
