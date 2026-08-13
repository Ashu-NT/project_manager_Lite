pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: detailRoot

    property var organization: ({})
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal actionRequested(string actionId)

    readonly property var _orgState: (detailRoot.organization && detailRoot.organization.state)
        ? detailRoot.organization.state
        : ({})
    readonly property string _orgTitle: String(detailRoot.organization && detailRoot.organization.title
        ? detailRoot.organization.title
        : "Organization")
    readonly property string _orgStatus: String(detailRoot.organization && detailRoot.organization.statusLabel
        ? detailRoot.organization.statusLabel
        : "")
    readonly property string _orgSubtitle: String(detailRoot.organization && detailRoot.organization.subtitle
        ? detailRoot.organization.subtitle
        : "")
    readonly property string _orgMetaText: String(detailRoot.organization && detailRoot.organization.metaText
        ? detailRoot.organization.metaText
        : "")
    readonly property bool _isActiveOrganization: detailRoot._orgState.isActive === true
    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Runtime Scope" },
        { "label": "Audit" }
    ]
    readonly property string _activeSectionLabel: {
        const section = detailRoot._sections[detailRoot.activeSectionIndex]
        return section ? String(section.label || "") : "Overview"
    }
    readonly property string _toolbarSubtitle: {
        if (detailRoot._activeSectionLabel === "Overview") {
            return detailRoot._orgSubtitle
        }
        if (detailRoot._activeSectionLabel === "Runtime Scope") {
            return "Shared platform records resolve through the active organization context."
        }
        return "Entity-level audit detail is still routed through the shared audit workspace."
    }
    readonly property var _toolbarActions: {
        const actions = []
        if (detailRoot._activeSectionLabel === "Overview") {
            actions.push({ "id": "edit", "label": "Edit", "icon": "edit" })
            if (!detailRoot._isActiveOrganization) {
                actions.push({ "id": "set_active", "label": "Set Active", "icon": "approve" })
            }
            actions.push({ "id": "refresh", "label": "Refresh", "icon": "refresh" })
            return actions
        }
        if (detailRoot._activeSectionLabel === "Runtime Scope") {
            actions.push({ "id": "refresh", "label": "Refresh", "icon": "refresh" })
            if (!detailRoot._isActiveOrganization) {
                actions.push({ "id": "set_active", "label": "Set Active", "icon": "approve" })
            }
            return actions
        }
        actions.push({ "id": "show_audit", "label": "Open Audit", "icon": "chevron_right" })
        return actions
    }
    readonly property var _overviewFields: [
        { "label": "Organization Code", "value": String(detailRoot._orgState.organizationCode || "-") },
        { "label": "Display Name", "value": String(detailRoot._orgState.displayName || detailRoot._orgTitle || "-") },
        { "label": "Timezone", "value": String(detailRoot._orgState.timezoneName || "-") },
        { "label": "Base Currency", "value": String(detailRoot._orgState.baseCurrency || "-") },
        { "label": "Status", "value": detailRoot._orgStatus.length > 0 ? detailRoot._orgStatus : "Unknown" },
        { "label": "Version", "value": String(detailRoot._orgState.version || "-") }
    ]

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: detailRoot._orgTitle
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
                                    implicitHeight: overviewGrid.implicitHeight + (Theme.AppTheme.spacingMd * 2)
                                    title: "Organization Summary"
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
                                            model: detailRoot._overviewFields

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
                                                    text: String(modelData.value || "-")
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
                                    implicitHeight: summaryColumn.implicitHeight + (Theme.AppTheme.spacingMd * 2)
                                    title: "Operational Notes"
                                    outlined: true

                                    ColumnLayout {
                                        id: summaryColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        AppWidgets.StatusChip {
                                            visible: detailRoot._orgStatus.length > 0
                                            status: detailRoot._orgStatus
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            visible: detailRoot.organization.supportingText ? true : false
                                            text: String(detailRoot.organization.supportingText || "")
                                            color: Theme.AppTheme.textSecondary
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            visible: detailRoot._orgMetaText.length > 0
                                            text: detailRoot._orgMetaText
                                            color: Theme.AppTheme.textMuted
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }

                                        AppWidgets.InlineMessage {
                                            Layout.fillWidth: true
                                            tone: detailRoot._isActiveOrganization ? "success" : "info"
                                            message: detailRoot._isActiveOrganization
                                                ? "This organization is the active runtime scope for shared Platform records."
                                                : "This organization is currently inactive. Activate it when you need it to become the runtime scope."
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
            implicitHeight: detailRoot.activeSectionIndex === 1 ? runtimeLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: runtimeLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading runtime scope..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading {
                            width: parent.width
                            label: "Runtime Scope"
                        }

                        Item {
                            width: parent.width
                            implicitHeight: runtimeColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: runtimeColumn
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
                                    message: "Shared platform APIs for sites, departments, documents, and downstream records resolve through the active organization context."
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: runtimeNotes.implicitHeight + (Theme.AppTheme.spacingMd * 2)
                                    title: "Context Resolution"
                                    outlined: true

                                    ColumnLayout {
                                        id: runtimeNotes
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: Theme.AppTheme.marginMd
                                        spacing: Theme.AppTheme.spacingSm

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: detailRoot._isActiveOrganization
                                                ? "This organization is active, so shared runtime catalogs resolve from this organization context."
                                                : "This organization is currently inactive. Shared runtime catalogs will resolve through the current active organization instead."
                                            color: Theme.AppTheme.textSecondary
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: "Current resolution chain: organization context -> shared sites -> shared departments -> shared documents -> downstream module integrations."
                                            color: Theme.AppTheme.textMuted
                                            font.pixelSize: Theme.AppTheme.captionSize
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
            width: parent ? parent.width : detailRoot.width
            implicitHeight: detailRoot.activeSectionIndex === 2 ? auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: auditLoader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                active: detailRoot.activeSectionIndex === 2
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
                                    message: "Entity-level organization audit trails are still delivered through the shared Platform audit workspace."
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: auditNotes.implicitHeight + (Theme.AppTheme.spacingMd * 2)
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
                                            text: "Use the shared audit workspace to inspect platform-wide events, approval history, and related operational activity for this organization."
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
