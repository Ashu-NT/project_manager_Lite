pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "../components"

Item {
    id: root

    property var party: ({})
    property bool inventoryEnabled: false
    property bool pmEnabled: false
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)

    readonly property var _state: (root.party && root.party.state) ? root.party.state : ({})
    readonly property string _title: String(root.party && root.party.title ? root.party.title : "Party")
    readonly property string _status: String(root.party && root.party.statusLabel ? root.party.statusLabel : "")
    readonly property string _subtitle: String(root.party && root.party.subtitle ? root.party.subtitle : "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property string _partyType: String(root._state.partyType || "")
    readonly property var _sections: {
        const sections = [
            { "label": "Overview" },
            { "label": "Contacts" }
        ]
        if (root.inventoryEnabled) {
            sections.push({ "label": "Supplier Profile" })
        }
        sections.push({ "label": "Customer / Client Profile" })
        if (root.pmEnabled) {
            sections.push({ "label": "Linked Projects" })
        }
        if (root.inventoryEnabled) {
            sections.push({ "label": "Linked Procurement" })
        }
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
        case "Contacts":
            return "Shared platform contact and address information used across modules by reference."
        case "Supplier Profile":
            return "Supplier-facing procurement posture remains governed by Inventory & Procurement."
        case "Customer / Client Profile":
            return "Customer and client master-data posture remains platform-owned for downstream commercial workflows."
        case "Linked Projects":
            return "Project relationships remain governed by the Project Management module."
        case "Linked Procurement":
            return "Procurement transactions and supplier usage remain governed by Inventory & Procurement."
        case "Documents":
            return "Party-linked document governance stays in the shared document workspace."
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
        if (root._activeSectionLabel === "Linked Projects") {
            return [
                { "id": "open_projects", "label": "Open Projects", "icon": "chevron_right" }
            ]
        }
        if (root._activeSectionLabel === "Linked Procurement") {
            return [
                { "id": "open_procurement", "label": "Open Procurement", "icon": "chevron_right" }
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
        { "label": "Party Code", "value": root._state.partyCode },
        { "label": "Party Name", "value": root._state.partyName || root.party.title },
        { "label": "Party Type", "value": root._partyType },
        { "label": "Legal Name", "value": root._state.legalName },
        { "label": "Status", "value": root._status },
        { "label": "Version", "value": root._state.version },
        { "label": "External Reference", "value": root._state.externalReference },
        { "label": "Tax Registration", "value": root._state.taxRegistrationNumber }
    ]
    readonly property var _contactFields: [
        { "label": "Contact Name", "value": root._state.contactName },
        { "label": "Email", "value": root._state.email },
        { "label": "Phone", "value": root._state.phone },
        { "label": "Address Line 1", "value": root._state.addressLine1 },
        { "label": "Address Line 2", "value": root._state.addressLine2 },
        { "label": "Postal Code", "value": root._state.postalCode },
        { "label": "City", "value": root._state.city },
        { "label": "Country", "value": root._state.country },
        { "label": "Website", "value": root._state.website }
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
                loadingMessage: "Loading party overview..."
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
                                    title: "Commercial Summary"
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
                                            text: String(root._state.notes || root.party.supportingText || "Party records stay platform-owned. Procurement, maintenance, and PM should reference these masters rather than duplicating them.")
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
            implicitHeight: root._activeSectionLabel === "Contacts" ? contactsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: contactsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Contacts"
                keepLoaded: true
                loadingMessage: "Loading contact profile..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Contacts"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: contactsColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: contactsColumn
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.topMargin: Theme.AppTheme.spacingMd
                                anchors.leftMargin: Theme.AppTheme.spacingMd
                                anchors.rightMargin: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: contactsGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Contact & Address"
                                    outlined: true

                                    GridLayout {
                                        id: contactsGrid
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        columns: 2
                                        columnSpacing: Theme.AppTheme.spacingLg
                                        rowSpacing: Theme.AppTheme.spacingSm

                                        Repeater {
                                            model: root._contactFields

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
                            }
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Supplier Profile" ? supplierLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: supplierLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Supplier Profile"
                keepLoaded: true
                loadingMessage: "Loading supplier profile..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Supplier Profile"
                        infoMessage: "Supplier-specific procurement posture is governed by Inventory & Procurement."
                        cardTitle: "Procurement Boundary"
                        notes: [
                            "Use Inventory & Procurement to validate whether this party is acting as a supplier, vendor, contractor, or service provider.",
                            "Supplier usage, purchasing history, and approval workflows should remain in the Procurement workspace.",
                            root._partyType.length > 0 ? ("Current party type: " + root._partyType) : "Current party type is not explicitly set on this record."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Customer / Client Profile" ? customerLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: customerLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Customer / Client Profile"
                keepLoaded: true
                loadingMessage: "Loading customer profile..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Customer / Client Profile"
                        infoMessage: "Customer and client semantics remain platform-owned and should be referenced by downstream modules."
                        cardTitle: "Commercial Context"
                        notes: [
                            "Use this record as the shared commercial identity for client, customer, and partner references across modules.",
                            "Project Management should reference client parties by ID instead of maintaining a separate client master.",
                            root._state.legalName ? ("Legal name: " + root._state.legalName) : "No legal-name override is stored on this record."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Linked Projects" ? projectsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: projectsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Linked Projects"
                keepLoaded: true
                loadingMessage: "Loading project linkage guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Linked Projects"
                        infoMessage: "Project/client and party-linked project behavior remains governed by the Project Management module."
                        cardTitle: "PM Boundary"
                        notes: [
                            "Open the Project Management workspace to inspect projects that reference this party as a client or commercial counterparty.",
                            "Platform Admin should not duplicate project lists or project-level CRUD here."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root._activeSectionLabel === "Linked Procurement" ? procurementLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: procurementLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root._activeSectionLabel === "Linked Procurement"
                keepLoaded: true
                loadingMessage: "Loading procurement linkage guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Linked Procurement"
                        infoMessage: "Procurement transactions and supplier usage remain governed by Inventory & Procurement."
                        cardTitle: "Procurement Boundary"
                        notes: [
                            "Open Inventory & Procurement to review purchase orders, requisitions, and supplier usage tied to this party.",
                            "Platform Admin should not duplicate procurement-ledger or receiving views here."
                        ]
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
                        infoMessage: "Party-linked document governance stays in the shared document workspace."
                        cardTitle: "Document Governance"
                        notes: [
                            "Use the shared Documents workspace for attachment, revision, and permission management.",
                            "Platform Admin should not duplicate document lifecycle workflows in the party detail page."
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
                        infoMessage: "Party audit trails stay centralized in the shared audit workspace."
                        cardTitle: "Audit Boundary"
                        notes: [
                            "Use the Audit workspace for actor history, change payloads, and export workflows.",
                            "Party detail pages should link into shared audit flows rather than duplicate audit storage."
                        ]
                    }
                }
            }
        }
    }
}
