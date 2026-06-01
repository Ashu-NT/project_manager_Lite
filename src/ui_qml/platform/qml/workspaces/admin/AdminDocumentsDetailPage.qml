pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers

Item {
    id: root

    property var document: ({})
    property var selectedDocument: ({})
    property var documentPreviewState: ({})
    property var documentLinkCatalog: ({})
    property var documentStructureCatalog: ({})
    property PlatformControllers.PlatformAdminWorkspaceController workspaceController
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)
    signal documentLinkCreateRequested()
    signal documentStructureCreateRequested()
    signal documentStructureEditRequested(string itemId)

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
        { "label": "Links & Structures" },
        { "label": "Audit" }
    ]
    readonly property string _activeSectionLabel: {
        const section = root._sections[root.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property string _toolbarSubtitle: {
        if (root._activeSectionLabel === "Overview") {
            return root._subtitle
        }
        if (root._activeSectionLabel === "Links & Structures") {
            return "Linked records, structure governance, and preview context for this document."
        }
        return "Entity-level document audit detail is still routed through the shared Platform audit workspace."
    }
    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview") {
            return [
                { "id": "edit", "label": "Edit", "icon": "edit" },
                { "id": "toggle_active", "label": root._isActive ? "Set Inactive" : "Set Active", "icon": "approve" },
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        if (root._activeSectionLabel === "Links & Structures") {
            return [
                { "id": "refresh", "label": "Refresh", "icon": "refresh" }
            ]
        }
        return [
            { "id": "show_audit", "label": "Open Audit", "icon": "chevron_right" }
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

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: badgesColumn.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Document Summary"
                                    outlined: true

                                    ColumnLayout {
                                        id: badgesColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        AppWidgets.StatusChip {
                                            visible: root._status.length > 0
                                            status: root._status
                                        }

                                        Flow {
                                            width: parent.width
                                            spacing: Theme.AppTheme.spacingSm

                                            Repeater {
                                                model: root.selectedDocument && root.selectedDocument.badges
                                                    ? root.selectedDocument.badges
                                                    : []

                                                delegate: Rectangle {
                                                    required property var modelData
                                                    radius: Theme.AppTheme.radiusSm
                                                    color: Theme.AppTheme.surfaceOverlay
                                                    border.color: Theme.AppTheme.divider
                                                    border.width: 1
                                                    implicitWidth: badgeRow.implicitWidth + Theme.AppTheme.spacingSm * 2
                                                    implicitHeight: badgeRow.implicitHeight + Theme.AppTheme.spacingXs * 2

                                                    Row {
                                                        id: badgeRow
                                                        anchors.centerIn: parent
                                                        spacing: Theme.AppTheme.spacingXs

                                                        AppControls.Label {
                                                            text: String(modelData.label || "")
                                                            color: Theme.AppTheme.textMuted
                                                            font.pixelSize: Theme.AppTheme.captionSize
                                                            font.bold: true
                                                        }

                                                        AppControls.Label {
                                                            text: String(modelData.value || "-")
                                                            color: Theme.AppTheme.textPrimary
                                                            font.pixelSize: Theme.AppTheme.captionSize
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: root.document.supportingText || root.document.metaText || "This governed document is managed through the shared platform document catalog."
                                            color: Theme.AppTheme.textSecondary
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
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
            implicitHeight: root.activeSectionIndex === 1 ? linksLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: linksLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading document links..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Links & Structures"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: documentSection.implicitHeight + Theme.AppTheme.spacingMd * 2

                            AdminDocumentSection {
                                id: documentSection
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.topMargin: Theme.AppTheme.spacingMd
                                anchors.leftMargin: Theme.AppTheme.spacingMd
                                anchors.rightMargin: Theme.AppTheme.spacingMd
                                workspaceController: root.workspaceController
                                selectedDocument: root.selectedDocument
                                documentPreviewState: root.documentPreviewState
                                documentLinkCatalog: root.documentLinkCatalog
                                documentStructureCatalog: root.documentStructureCatalog
                                onDocumentLinkCreateRequested: root.documentLinkCreateRequested()
                                onDocumentStructureCreateRequested: root.documentStructureCreateRequested()
                                onDocumentStructureEditRequested: function(itemId) {
                                    root.documentStructureEditRequested(itemId)
                                }
                            }
                        }
                    }
                }
            }
        }

        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 2 ? auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: root.activeSectionIndex === 2
                keepLoaded: true
                loadingMessage: "Loading audit guidance..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Audit"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: auditColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: auditColumn
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
                                    message: "Entity-level document audit trails are still delivered through the shared Platform audit workspace."
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: auditNotes.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Audit Follow-up"
                                    outlined: true

                                    ColumnLayout {
                                        id: auditNotes
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: "Use the shared audit workspace to inspect approvals, revisions, and operational activity associated with this document."
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
    }
}
