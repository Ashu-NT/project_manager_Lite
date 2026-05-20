import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets

AppLayouts.WorkspaceFrame {
    id: root

    // ── Public API (backward-compatible) ─────────────────────────
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var workspaceModel: root.platformCatalog
        ? root.platformCatalog.workspace("platform.admin")
        : ({
            "routeId": "platform.admin",
            "title": "Admin Console",
            "summary": ""
        })
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.adminWorkspace
        : null
    property PlatformControllers.PlatformAdminAccessWorkspaceController accessController: root.platformCatalog
        ? root.platformCatalog.adminAccessWorkspace
        : null
    property PlatformControllers.PlatformSupportWorkspaceController supportController: root.platformCatalog
        ? root.platformCatalog.adminSupportWorkspace
        : null
    property var organizationCatalog: root.workspaceController
        ? root.workspaceController.organizations
        : ({ "title": "Organizations", "subtitle": "", "emptyState": "", "items": [] })
    property var siteCatalog: root.workspaceController
        ? root.workspaceController.sites
        : ({ "title": "Sites", "subtitle": "", "emptyState": "", "items": [] })
    property var departmentCatalog: root.workspaceController
        ? root.workspaceController.departments
        : ({ "title": "Departments", "subtitle": "", "emptyState": "", "items": [] })
    property var employeeCatalog: root.workspaceController
        ? root.workspaceController.employees
        : ({ "title": "Employees", "subtitle": "", "emptyState": "", "items": [] })
    property var userCatalog: root.workspaceController
        ? root.workspaceController.users
        : ({ "title": "Users", "subtitle": "", "emptyState": "", "items": [] })
    property var partyCatalog: root.workspaceController
        ? root.workspaceController.parties
        : ({ "title": "Parties", "subtitle": "", "emptyState": "", "items": [] })
    property var documentCatalog: root.workspaceController
        ? root.workspaceController.documents
        : ({ "title": "Documents", "subtitle": "", "emptyState": "", "items": [] })
    property var selectedDocument: root.workspaceController
        ? root.workspaceController.selectedDocument
        : ({ "hasSelection": false, "documentId": "", "title": "Select a document",
             "summary": "", "badges": [], "metadataRows": [], "notes": "" })
    property var documentPreviewState: root.workspaceController
        ? root.workspaceController.documentPreview
        : ({ "statusLabel": "No document selected", "summary": "",
             "canOpen": false, "openLabel": "Open Source", "openTargetUrl": "" })
    property var documentLinkCatalog: root.workspaceController
        ? root.workspaceController.documentLinks
        : ({ "title": "Linked Records", "subtitle": "", "emptyState": "", "items": [] })
    property var documentStructureCatalog: root.workspaceController
        ? root.workspaceController.documentStructures
        : ({ "title": "Document Structures", "subtitle": "", "emptyState": "", "items": [] })

    // ── Navigation & selection state ──────────────────────────────
    property string _activeSection: "organizations"
    property string _selectedRowId: ""

    readonly property bool _detailOpen: {
        const s = root._activeSection
        return root._selectedRowId.length > 0
            && s !== "access" && s !== "support" && s !== "audit"
    }

    readonly property var _detailItem: {
        const section = root._activeSection
        const rowId   = root._selectedRowId
        if (!rowId) return null
        let cat = null
        if      (section === "organizations") cat = root.organizationCatalog
        else if (section === "sites")         cat = root.siteCatalog
        else if (section === "departments")   cat = root.departmentCatalog
        else if (section === "employees")     cat = root.employeeCatalog
        else if (section === "users")         cat = root.userCatalog
        else if (section === "parties")       cat = root.partyCatalog
        else if (section === "documents")     cat = root.documentCatalog
        else if (section === "structures")    cat = root.documentStructureCatalog
        if (!cat) return null
        const items = cat.items || []
        for (let i = 0; i < items.length; i++) {
            if (String(items[i].id) === String(rowId)) return items[i]
        }
        return null
    }

    readonly property var _entityColumns: [
        { key: "title",       label: "Name",    flex: 3, minWidth: 160, sortable: true,  visible: true },
        { key: "subtitle",    label: "Details", flex: 3, minWidth: 120, sortable: false, visible: true },
        { key: "statusLabel", label: "Status",  flex: 0, minWidth: 90,  sortable: false, visible: true,
          type: "status" },
        { key: "metaText",    label: "Info",    flex: 2, minWidth: 120, sortable: false, visible: true }
    ]

    readonly property bool   _busy: root.workspaceController ? root.workspaceController.isBusy        : false
    readonly property bool   _load: root.workspaceController ? root.workspaceController.isLoading     : false
    readonly property string _err:  root.workspaceController ? root.workspaceController.errorMessage  : ""
    readonly property string _ok:   root.workspaceController ? root.workspaceController.feedbackMessage : ""

    // ── Helper functions ──────────────────────────────────────────
    function catalogItemById(catalog, itemId) {
        const items = catalog.items || []
        for (let i = 0; i < items.length; i++) {
            if (items[i].id === itemId) return items[i]
        }
        return null
    }

    function openOrganizationEdit(itemId) {
        const item = root.catalogItemById(root.organizationCatalog, itemId)
        if (item !== null) dialogHost.openOrganizationEdit(item.state || {})
    }

    function openSiteEdit(itemId) {
        const item = root.catalogItemById(root.siteCatalog, itemId)
        if (item !== null) dialogHost.openSiteEdit(item.state || {})
    }

    function openDepartmentEdit(itemId) {
        const item = root.catalogItemById(root.departmentCatalog, itemId)
        if (item !== null) dialogHost.openDepartmentEdit(item.state || {})
    }

    function openEmployeeEdit(itemId) {
        const item = root.catalogItemById(root.employeeCatalog, itemId)
        if (item !== null) dialogHost.openEmployeeEdit(item.state || {})
    }

    function openUserEdit(itemId) {
        const item = root.catalogItemById(root.userCatalog, itemId)
        if (item !== null) dialogHost.openUserEdit(item.state || {})
    }

    function openPartyEdit(itemId) {
        const item = root.catalogItemById(root.partyCatalog, itemId)
        if (item !== null) dialogHost.openPartyEdit(item.state || {})
    }

    function inspectDocument(itemId) {
        if (root.workspaceController !== null) root.workspaceController.selectDocument(itemId)
    }

    function openDocumentEdit(itemId) {
        const item = root.catalogItemById(root.documentCatalog, itemId)
        if (item !== null) {
            root.inspectDocument(itemId)
            dialogHost.openDocumentEdit(item.state || {})
        }
    }

    function openDocumentLinkCreate() {
        if (root.selectedDocument.hasSelection)
            dialogHost.openDocumentLinkCreate(root.selectedDocument.documentId || "")
    }

    function openDocumentStructureEdit(itemId) {
        const item = root.catalogItemById(root.documentStructureCatalog, itemId)
        if (item !== null) dialogHost.openDocumentStructureEdit(item.state || {})
    }

    title: root.workspaceController
        ? (root.workspaceController.overview.title || root.workspaceModel.title)
        : root.workspaceModel.title
    subtitle: root.workspaceController ? root.workspaceController.overview.subtitle : ""

    // ── Shell layout ──────────────────────────────────────────────
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ── Left navigation sidebar ───────────────────────────────
        AdminNavSidebar {
            id: _sidebar
            Layout.fillHeight:     true
            Layout.preferredWidth: implicitWidth
            activeSection: root._activeSection
            onSectionChanged: function(section) {
                root._activeSection = section
                root._selectedRowId = ""
            }
        }

        // ── Center workspace ──────────────────────────────────────
        Item {
            Layout.fillWidth:  true
            Layout.fillHeight: true

            // ── Organizations ─────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "organizations"
                sectionTitle:    "Organizations"
                entityLabel:     "Organization"
                catalog:         root.organizationCatalog
                columns:         root._entityColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHost.openOrganizationCreate()
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openOrganizationEdit(id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Sites ─────────────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "sites"
                sectionTitle:    "Sites"
                entityLabel:     "Site"
                catalog:         root.siteCatalog
                columns:         root._entityColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHost.openSiteCreate()
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openSiteEdit(id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Departments ───────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "departments"
                sectionTitle:    "Departments"
                entityLabel:     "Department"
                catalog:         root.departmentCatalog
                columns:         root._entityColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHost.openDepartmentCreate()
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openDepartmentEdit(id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Employees ─────────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "employees"
                sectionTitle:    "Employees"
                entityLabel:     "Employee"
                catalog:         root.employeeCatalog
                columns:         root._entityColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHost.openEmployeeCreate()
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openEmployeeEdit(id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Users ─────────────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "users"
                sectionTitle:    "Users"
                entityLabel:     "User"
                catalog:         root.userCatalog
                columns:         root._entityColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHost.openUserCreate()
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openUserEdit(id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Parties ───────────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "parties"
                sectionTitle:    "Parties"
                entityLabel:     "Party"
                catalog:         root.partyCatalog
                columns:         root._entityColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHost.openPartyCreate()
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openPartyEdit(id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Documents ─────────────────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "documents"
                sectionTitle:    "Documents"
                entityLabel:     "Document"
                catalog:         root.documentCatalog
                columns:         root._entityColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHost.openDocumentCreate()
                onRowSelected:      function(id) {
                    root._selectedRowId = id
                    root.inspectDocument(id)
                }
                onRowActivated:     function(id) { root.openDocumentEdit(id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Document Structures ───────────────────────────────
            AdminEntityWorkspace {
                anchors.fill:    parent
                visible:         root._activeSection === "structures"
                sectionTitle:    "Document Structures"
                entityLabel:     "Structure"
                catalog:         root.documentStructureCatalog
                columns:         root._entityColumns
                isBusy:          root._busy
                isLoading:       root._load
                errorMessage:    root._err
                feedbackMessage: root._ok
                selectedRowId:   root._selectedRowId

                onCreateRequested:  dialogHost.openDocumentStructureCreate()
                onRowSelected:      function(id) { root._selectedRowId = id }
                onRowActivated:     function(id) { root.openDocumentStructureEdit(id) }
                onRefreshRequested: { if (root.workspaceController) root.workspaceController.refresh() }
            }

            // ── Roles & Access ────────────────────────────────────
            Item {
                anchors.fill: parent
                visible:      root._activeSection === "access"
                clip:         true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        height: Theme.AppTheme.toolbarHeight - 6
                        color:  Theme.AppTheme.surfaceRaised
                        z:      1

                        Rectangle {
                            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                            height: 1; color: Theme.AppTheme.divider
                        }

                        RowLayout {
                            anchors.fill:        parent
                            anchors.leftMargin:  Theme.AppTheme.marginMd
                            anchors.rightMargin: 8
                            spacing: Theme.AppTheme.spacingXs

                            Label {
                                text:           "Roles & Access"
                                color:          Theme.AppTheme.textPrimary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold:      true
                            }
                            Item { Layout.fillWidth: true }
                            AppControls.SecondaryButton {
                                text:     "Refresh"
                                iconName: "refresh"
                                enabled:  root.accessController ? !root.accessController.isBusy : false
                                onClicked: { if (root.accessController) root.accessController.refresh() }
                            }
                        }
                    }

                    Flickable {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        contentWidth:      width
                        contentHeight:     _accessPanel.implicitHeight + (2 * Theme.AppTheme.marginLg)
                        clip:              true
                        boundsBehavior:    Flickable.StopAtBounds

                        PlatformWidgets.AccessSecurityPanel {
                            id: _accessPanel
                            anchors.left:    parent.left
                            anchors.right:   parent.right
                            anchors.top:     parent.top
                            anchors.margins: Theme.AppTheme.marginLg
                            controller:      root.accessController
                        }
                    }
                }
            }

            // ── Support ───────────────────────────────────────────
            Item {
                anchors.fill: parent
                visible:      root._activeSection === "support"
                clip:         true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        height: Theme.AppTheme.toolbarHeight - 6
                        color:  Theme.AppTheme.surfaceRaised
                        z:      1

                        Rectangle {
                            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                            height: 1; color: Theme.AppTheme.divider
                        }

                        Label {
                            anchors.left:           parent.left
                            anchors.leftMargin:     Theme.AppTheme.marginMd
                            anchors.verticalCenter: parent.verticalCenter
                            text:           "Support"
                            color:          Theme.AppTheme.textPrimary
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold:      true
                        }
                    }

                    Flickable {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        contentWidth:      width
                        contentHeight:     _supportSection.implicitHeight + (2 * Theme.AppTheme.marginLg)
                        clip:              true
                        boundsBehavior:    Flickable.StopAtBounds

                        AdminSupportSection {
                            id: _supportSection
                            anchors.left:    parent.left
                            anchors.right:   parent.right
                            anchors.top:     parent.top
                            anchors.margins: Theme.AppTheme.marginLg
                            supportController: root.supportController
                        }
                    }
                }
            }

            // ── Audit / Overview ──────────────────────────────────
            Item {
                anchors.fill: parent
                visible:      root._activeSection === "audit"
                clip:         true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        Layout.fillWidth: true
                        height: Theme.AppTheme.toolbarHeight - 6
                        color:  Theme.AppTheme.surfaceRaised
                        z:      1

                        Rectangle {
                            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                            height: 1; color: Theme.AppTheme.divider
                        }

                        RowLayout {
                            anchors.fill:        parent
                            anchors.leftMargin:  Theme.AppTheme.marginMd
                            anchors.rightMargin: 8
                            spacing: Theme.AppTheme.spacingXs

                            Label {
                                text:           "Audit & Overview"
                                color:          Theme.AppTheme.textPrimary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold:      true
                            }
                            Item { Layout.fillWidth: true }
                            AppControls.SecondaryButton {
                                text:     "Refresh"
                                iconName: "refresh"
                                enabled:  root.workspaceController ? !root.workspaceController.isBusy : false
                                onClicked: { if (root.workspaceController) root.workspaceController.refresh() }
                            }
                        }
                    }

                    Flickable {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        contentWidth:      width
                        contentHeight:     _auditColumn.implicitHeight + (2 * Theme.AppTheme.marginLg)
                        clip:              true
                        boundsBehavior:    Flickable.StopAtBounds

                        ColumnLayout {
                            id: _auditColumn
                            anchors.left:    parent.left
                            anchors.right:   parent.right
                            anchors.top:     parent.top
                            anchors.margins: Theme.AppTheme.marginLg
                            spacing:         Theme.AppTheme.spacingMd

                            PlatformWidgets.WorkspaceStateBanner {
                                Layout.fillWidth: true
                                isLoading:       root._load
                                isBusy:          root._busy
                                errorMessage:    root._err
                                feedbackMessage: root._ok
                            }

                            AdminMetricsSection {
                                Layout.fillWidth: true
                                metrics: root.workspaceController
                                    ? (root.workspaceController.overview.metrics || []) : []
                            }

                            AdminOverviewSections {
                                Layout.fillWidth: true
                                sections: root.workspaceController
                                    ? (root.workspaceController.overview.sections || []) : []
                            }
                        }
                    }
                }
            }
        }

        // ── Right detail panel ────────────────────────────────────
        Rectangle {
            id: _detailPanel
            Layout.fillHeight:     true
            Layout.preferredWidth: 288
            visible:               root._detailOpen
            color:                 Theme.AppTheme.surface
            z:                     1

            Rectangle {
                anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                width: 1; color: Theme.AppTheme.divider
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Panel header
                Rectangle {
                    Layout.fillWidth: true
                    height: Theme.AppTheme.toolbarHeight - 6
                    color:  Theme.AppTheme.surfaceRaised

                    Rectangle {
                        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                        height: 1; color: Theme.AppTheme.divider
                    }

                    Label {
                        anchors.left:           parent.left
                        anchors.leftMargin:     Theme.AppTheme.marginMd
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right:          _closeBtn.left
                        anchors.rightMargin:    4
                        text:           root._detailItem ? (root._detailItem.title || "Details") : "Details"
                        color:          Theme.AppTheme.textPrimary
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold:      true
                        elide:          Text.ElideRight
                    }

                    Rectangle {
                        id: _closeBtn
                        anchors.right:          parent.right
                        anchors.rightMargin:    6
                        anchors.verticalCenter: parent.verticalCenter
                        width: 26; height: 26; radius: 4
                        color: _closeMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                        AppIcons.AppIcon {
                            anchors.centerIn: parent
                            name: "close"; size: 10
                            iconColor: Theme.AppTheme.textMuted
                        }

                        MouseArea {
                            id: _closeMA
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape:  Qt.PointingHandCursor
                            onClicked:    root._selectedRowId = ""
                        }
                    }
                }

                // Panel body (scrollable)
                Flickable {
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    contentWidth:      width
                    contentHeight:     _panelContent.implicitHeight
                    clip:              true
                    boundsBehavior:    Flickable.StopAtBounds

                    ColumnLayout {
                        id: _panelContent
                        width: parent.width
                        spacing: 0

                        // ── Document inspector ────────────────────────────
                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: root._activeSection === "documents"
                            spacing: 0

                            PlatformWidgets.DocumentDetailPanel {
                                Layout.fillWidth: true
                                details:         root.selectedDocument
                                previewState:    root.documentPreviewState
                                actionsEnabled:  root.workspaceController
                                    ? !root.workspaceController.isBusy : false
                                onOpenRequested: function(url) {
                                    if (url && url.length > 0) Qt.openUrlExternally(url)
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1; color: Theme.AppTheme.divider
                            }

                            // Document actions
                            RowLayout {
                                Layout.fillWidth:    true
                                Layout.leftMargin:   Theme.AppTheme.marginMd
                                Layout.rightMargin:  Theme.AppTheme.marginMd
                                Layout.topMargin:    Theme.AppTheme.spacingSm
                                Layout.bottomMargin: Theme.AppTheme.spacingXs
                                spacing: Theme.AppTheme.spacingXs

                                AppControls.PrimaryButton {
                                    Layout.fillWidth: true
                                    text:     "Edit"
                                    iconName: "edit"
                                    enabled:  root.workspaceController ? !root.workspaceController.isBusy : false
                                    onClicked: root.openDocumentEdit(root._selectedRowId)
                                }

                                AppControls.SecondaryButton {
                                    text:     "Toggle"
                                    iconName: "approve"
                                    enabled:  root.workspaceController ? !root.workspaceController.isBusy : false
                                    onClicked: {
                                        if (root.workspaceController)
                                            root.workspaceController.toggleDocumentActive(root._selectedRowId)
                                    }
                                }
                            }

                            AppControls.SecondaryButton {
                                Layout.fillWidth:    true
                                Layout.leftMargin:   Theme.AppTheme.marginMd
                                Layout.rightMargin:  Theme.AppTheme.marginMd
                                Layout.bottomMargin: Theme.AppTheme.spacingSm
                                text:     "Delete"
                                iconName: "delete"
                                danger:   true
                                enabled:  root.workspaceController ? !root.workspaceController.isBusy : false
                                onClicked: { /* root.workspaceController.deleteDocument(root._selectedRowId) */ }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 1; color: Theme.AppTheme.divider
                            }

                            // Linked records header
                            RowLayout {
                                Layout.fillWidth:    true
                                Layout.leftMargin:   Theme.AppTheme.marginMd
                                Layout.rightMargin:  Theme.AppTheme.marginMd
                                Layout.topMargin:    Theme.AppTheme.spacingSm
                                Layout.bottomMargin: Theme.AppTheme.spacingSm
                                spacing: Theme.AppTheme.spacingSm

                                Label {
                                    Layout.fillWidth: true
                                    text:           "Linked Records"
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                }

                                Label {
                                    visible: (root.documentLinkCatalog.items || []).length > 0
                                    text:    String((root.documentLinkCatalog.items || []).length)
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }

                                AppControls.SecondaryButton {
                                    text:     "Add Link"
                                    iconName: "add"
                                    enabled:  root.selectedDocument.hasSelection
                                        && (root.workspaceController ? !root.workspaceController.isBusy : false)
                                    onClicked: root.openDocumentLinkCreate()
                                }
                            }

                            Repeater {
                                model: root.documentLinkCatalog.items || []

                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index

                                    width:  _panelContent.width
                                    height: 34
                                    color:  _linkRowMA.containsMouse
                                        ? Theme.AppTheme.hoverSurface : "transparent"

                                    Rectangle {
                                        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                        height: 1; color: Theme.AppTheme.divider
                                    }

                                    RowLayout {
                                        anchors.fill:        parent
                                        anchors.leftMargin:  Theme.AppTheme.marginMd
                                        anchors.rightMargin: Theme.AppTheme.marginSm
                                        spacing: Theme.AppTheme.spacingXs

                                        Label {
                                            Layout.fillWidth: true
                                            text:           modelData.title || ""
                                            color:          Theme.AppTheme.textPrimary
                                            font.family:    Theme.AppTheme.fontFamily
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            elide:          Text.ElideRight
                                        }

                                        Rectangle {
                                            width: 22; height: 22; radius: 4
                                            color: _removeLinkMA.containsMouse
                                                ? Theme.AppTheme.dangerSoft : "transparent"

                                            AppIcons.AppIcon {
                                                anchors.centerIn: parent
                                                name: "close"; size: 9
                                                iconColor: _removeLinkMA.containsMouse
                                                    ? Theme.AppTheme.danger
                                                    : Theme.AppTheme.textMuted
                                            }

                                            MouseArea {
                                                id: _removeLinkMA
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape:  Qt.PointingHandCursor
                                                enabled:      root.workspaceController
                                                    ? !root.workspaceController.isBusy : false
                                                onClicked: {
                                                    if (root.workspaceController)
                                                        root.workspaceController.removeDocumentLink(modelData.id)
                                                }
                                            }
                                        }
                                    }

                                    MouseArea {
                                        id: _linkRowMA
                                        anchors.fill: parent
                                        hoverEnabled: true
                                    }
                                }
                            }
                        }

                        // ── Generic entity inspector ──────────────────────
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.margins:   Theme.AppTheme.marginMd
                            visible:          root._activeSection !== "documents"
                            spacing:          Theme.AppTheme.spacingSm

                            // Entity name
                            Label {
                                Layout.fillWidth: true
                                text:           root._detailItem ? (root._detailItem.title || "") : ""
                                color:          Theme.AppTheme.textPrimary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.sectionSize
                                font.bold:      true
                                wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                            }

                            // Status chip
                            AppWidgets.StatusChip {
                                visible: root._detailItem
                                    ? (root._detailItem.statusLabel || "").length > 0 : false
                                status: root._detailItem ? (root._detailItem.statusLabel || "") : ""
                            }

                            // Divider
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.topMargin: 2; Layout.bottomMargin: 2
                                height: 1; color: Theme.AppTheme.divider
                            }

                            // Details field
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: root._detailItem
                                    ? (root._detailItem.subtitle || "").length > 0 : false

                                Label {
                                    text:           "Details"
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text:           root._detailItem ? (root._detailItem.subtitle || "") : ""
                                    color:          Theme.AppTheme.textSecondary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }

                            // Info field
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: root._detailItem
                                    ? (root._detailItem.metaText || "").length > 0 : false

                                Label {
                                    text:           "Info"
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text:           root._detailItem ? (root._detailItem.metaText || "") : ""
                                    color:          Theme.AppTheme.textSecondary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }

                            // Action divider
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.topMargin: 2
                                height: 1; color: Theme.AppTheme.divider
                                visible: root._detailItem !== null
                            }

                            // Primary actions: Edit + Set Active / Toggle
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs
                                visible: root._detailItem !== null

                                AppControls.PrimaryButton {
                                    Layout.fillWidth: true
                                    text:     "Edit"
                                    iconName: "edit"
                                    enabled:  !root._busy
                                    onClicked: {
                                        const id = root._selectedRowId
                                        const s  = root._activeSection
                                        if      (s === "organizations") root.openOrganizationEdit(id)
                                        else if (s === "sites")         root.openSiteEdit(id)
                                        else if (s === "departments")   root.openDepartmentEdit(id)
                                        else if (s === "employees")     root.openEmployeeEdit(id)
                                        else if (s === "users")         root.openUserEdit(id)
                                        else if (s === "parties")       root.openPartyEdit(id)
                                        else if (s === "structures")    root.openDocumentStructureEdit(id)
                                    }
                                }

                                AppControls.SecondaryButton {
                                    visible:  root._activeSection === "organizations"
                                    text:     "Set Active"
                                    iconName: "approve"
                                    enabled:  !root._busy
                                    onClicked: {
                                        if (root.workspaceController)
                                            root.workspaceController.setActiveOrganization(root._selectedRowId)
                                    }
                                }

                                AppControls.SecondaryButton {
                                    visible:  root._activeSection !== "organizations"
                                    text:     "Toggle"
                                    iconName: "approve"
                                    enabled:  !root._busy
                                    onClicked: {
                                        const id = root._selectedRowId
                                        const s  = root._activeSection
                                        if (!root.workspaceController) return
                                        if      (s === "sites")       root.workspaceController.toggleSiteActive(id)
                                        else if (s === "departments") root.workspaceController.toggleDepartmentActive(id)
                                        else if (s === "employees")   root.workspaceController.toggleEmployeeActive(id)
                                        else if (s === "users")       root.workspaceController.toggleUserActive(id)
                                        else if (s === "parties")     root.workspaceController.togglePartyActive(id)
                                        else if (s === "structures")  root.workspaceController.toggleDocumentStructureActive(id)
                                    }
                                }
                            }

                            // Delete action
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                visible:  root._detailItem !== null
                                text:     "Delete"
                                iconName: "delete"
                                danger:   true
                                enabled:  !root._busy
                                onClicked: { /* root.workspaceController.deleteEntity(root._selectedRowId) */ }
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Dialog host ───────────────────────────────────────────────
    AdminDialogHost {
        id: dialogHost
        workspaceController: root.workspaceController
    }
}
