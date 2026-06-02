pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets

Item {
    id: root

    property var document: ({})
    property var selectedDocument: ({})
    property var documentPreviewState: ({})
    property var documentLinkCatalog: ({})
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)
    signal documentLinkCreateRequested()

    readonly property var _state: (root.document && root.document.state) ? root.document.state : ({})
    readonly property string _title: String(root.selectedDocument && root.selectedDocument.title
        ? root.selectedDocument.title
        : (root.document && root.document.title ? root.document.title : "Document"))
    readonly property string _subtitle: String(root.selectedDocument && root.selectedDocument.summary
        ? root.selectedDocument.summary
        : (root.document && root.document.subtitle ? root.document.subtitle : ""))
    readonly property string _status: String(root.document && root.document.statusLabel ? root.document.statusLabel : "")
    readonly property bool _isActive: root._state.isActive === true
    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Revisions" },
        { "label": "Linked Entities", "count": (root.documentLinkCatalog.items || []).length },
        { "label": "Approvals" },
        { "label": "Access" },
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
        case "Revisions":
            return "Business version, source-system, and revision context for the governed document record."
        case "Linked Entities":
            return "Linked records stay entity-scoped while structure governance remains a separate shared admin concern."
        case "Approvals":
            return "Approval and workflow history stays governed by the shared Platform Control workspace."
        case "Access":
            return "Confidentiality, storage, and access posture stay governed through shared document controls."
        case "Audit":
            return "Entity-level document audit detail is routed through the shared Platform audit workspace."
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
        if (root._activeSectionLabel === "Linked Entities") {
            return [
                { "id": "create_document_link", "label": "Add Link", "icon": "add" }
            ]
        }
        if (root._activeSectionLabel === "Approvals") {
            return [
                { "id": "open_control", "label": "Open Control", "icon": "chevron_right" }
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
    readonly property var _overviewFields: {
        const rows = root.selectedDocument && root.selectedDocument.metadataRows
            ? root.selectedDocument.metadataRows
            : []
        if (rows.length > 0) {
            return rows
        }
        return [
            { "label": "Document Code", "value": root._state.documentCode },
            { "label": "Title", "value": root._state.title || root.document.title },
            { "label": "Document Type", "value": root._state.documentType },
            { "label": "Storage Kind", "value": root._state.storageKind },
            { "label": "Source System", "value": root._state.sourceSystem },
            { "label": "Version / Revision", "value": root._state.businessVersionLabel }
        ]
    }
    readonly property var _revisionRows: [
        { "label": "Version / Revision", "value": root._state.businessVersionLabel },
        { "label": "Source System", "value": root._state.sourceSystem },
        { "label": "MIME Type", "value": root._state.mimeType },
        { "label": "File Name", "value": root._state.fileName },
        { "label": "Notes", "value": root.selectedDocument && root.selectedDocument.notes ? root.selectedDocument.notes : root._state.notes }
    ]
    readonly property var _accessRows: [
        { "label": "Confidentiality", "value": root._state.confidentialityLevel },
        { "label": "Storage Kind", "value": root._state.storageKind },
        { "label": "Storage URI", "value": root._state.storageUri },
        { "label": "Source System", "value": root._state.sourceSystem },
        { "label": "Preview Status", "value": root.documentPreviewState.statusLabel }
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
                loadingMessage: "Loading document overview..."
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

                                PlatformWidgets.DocumentDetailPanel {
                                    Layout.fillWidth: true
                                    details: root.selectedDocument
                                    previewState: root.documentPreviewState
                                    actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
                                    onOpenRequested: function(targetUrl) {
                                        if (targetUrl && targetUrl.length > 0) {
                                            Qt.openUrlExternally(targetUrl)
                                        }
                                    }
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: metadataColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Metadata"
                                    outlined: true

                                    ColumnLayout {
                                        id: metadataColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        Repeater {
                                            model: root._overviewFields

                                            delegate: RowLayout {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                spacing: Theme.AppTheme.spacingSm

                                                AppControls.Label {
                                                    Layout.preferredWidth: 170
                                                    text: String(modelData.label || "")
                                                    color: Theme.AppTheme.textMuted
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    font.bold: true
                                                }

                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: String(modelData.value || "-")
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
            implicitHeight: root.activeSectionIndex === 1 ? revisionsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: revisionsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading revision context..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Revisions"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: revisionsColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: revisionsColumn
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
                                    message: "Revision history remains governed by the shared document lifecycle rather than a separate Platform Admin ledger."
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: revisionRows.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Current Revision Context"
                                    outlined: true

                                    ColumnLayout {
                                        id: revisionRows
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        Repeater {
                                            model: root._revisionRows

                                            delegate: RowLayout {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                spacing: Theme.AppTheme.spacingSm

                                                AppControls.Label {
                                                    Layout.preferredWidth: 170
                                                    text: String(modelData.label || "")
                                                    color: Theme.AppTheme.textMuted
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    font.bold: true
                                                }

                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: String(modelData.value || "-")
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
            implicitHeight: root.activeSectionIndex === 2 ? linksLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: linksLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 2
                keepLoaded: true
                loadingMessage: "Loading linked entities..."
                sourceComponent: Component {
                    AdminDetailTableSection {
                        width: parent ? parent.width : 0
                        sectionLabel: "Linked Entities"
                        infoMessage: "Entity links remain document-scoped; structure governance has been split back to the dedicated Structures workspace."
                        emptyTitle: "No linked records"
                        emptyMessage: root.documentLinkCatalog.emptyState || "No linked records are available for this document."
                        rows: root.documentLinkCatalog.items || []
                        columns: [
                            { "key": "title", "label": "Module / Entity", "flex": 3, "minWidth": 200, "sortable": true, "visible": true },
                            { "key": "subtitle", "label": "Entity ID", "flex": 2, "minWidth": 140, "sortable": false, "visible": true },
                            { "key": "statusLabel", "label": "Role", "flex": 0, "minWidth": 100, "sortable": false, "visible": true, "type": "status" },
                            { "key": "metaText", "label": "Document Ref", "flex": 2, "minWidth": 160, "sortable": false, "visible": true }
                        ]
                        loading: root.busy
                        tableHeight: root._tableHeightForCount((root.documentLinkCatalog.items || []).length)
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 3 ? approvalsLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: approvalsLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 3
                keepLoaded: true
                loadingMessage: "Loading approval guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Approvals"
                        infoMessage: "Approval workflows and controlled decisions remain governed by the shared Platform Control workspace."
                        cardTitle: "Approval Boundary"
                        notes: [
                            "Open Platform Control to inspect approval queues, decision history, and governed change requests tied to documents.",
                            "The admin document detail page should not duplicate approval workflow storage or actions."
                        ]
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 4 ? accessLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: accessLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 4
                keepLoaded: true
                loadingMessage: "Loading access posture..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Access"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: accessColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: accessColumn
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
                                    message: "Confidentiality and access posture are enforced through shared document controls and permission inheritance."
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: accessRows.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Access Posture"
                                    outlined: true

                                    ColumnLayout {
                                        id: accessRows
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        Repeater {
                                            model: root._accessRows

                                            delegate: RowLayout {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                spacing: Theme.AppTheme.spacingSm

                                                AppControls.Label {
                                                    Layout.preferredWidth: 170
                                                    text: String(modelData.label || "")
                                                    color: Theme.AppTheme.textMuted
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    font.bold: true
                                                }

                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: String(modelData.value || "-")
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
            implicitHeight: root.activeSectionIndex === 5 ? auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 5
                keepLoaded: true
                loadingMessage: "Loading audit guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Audit"
                        infoMessage: "Entity-level document audit trails are still delivered through the shared Platform audit workspace."
                        cardTitle: "Audit Follow-up"
                        notes: [
                            "Use the shared audit workspace to inspect approvals, revisions, and operational activity associated with this document."
                        ]
                    }
                }
            }
        }
    }
}
