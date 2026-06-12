pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets
import "sections" as Sections
import "panels" as Panels
import "components" as Components

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementRegisterWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.registerWorkspace
        : null

    // ── Models ─────────────────────────────────────────────────────────
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({ "routeId": "project_management.register", "title": "Register", "summary": "Risks, issues, and changes — unified project governance register." })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": root.workspaceModel.title, "subtitle": root.workspaceModel.summary, "metrics": [] })
    readonly property var entriesModel: root.workspaceController
        ? root.workspaceController.entries
        : ({ "title": "Project Register", "emptyState": "Select a project to review register entries.", "items": [] })
    readonly property var selectedEntryModel: root.workspaceController
        ? root.workspaceController.selectedEntry
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "emptyState": "Select a register entry to review governance details.", "fields": [], "state": {} })
    readonly property var urgentModel: root.workspaceController
        ? root.workspaceController.urgentEntries
        : ({ "title": "Urgent Review Queue", "subtitle": "", "emptyState": "No urgent register items.", "items": [] })

    title:    root.overviewModel.title    || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    // ── State ──────────────────────────────────────────────────────────
    RegisterWorkspaceState {
        id: state
        pmCatalog:           root.pmCatalog
        workspaceController: root.workspaceController
    }

    property bool _detailOpen:          false
    property int  _pendingDetailSection: 0
    readonly property var detailPage:   detailPageLoader.item

    // ── Dialog config (type-aware create) ─────────────────────────────
    readonly property string _activeType: root.workspaceController
        ? (root.workspaceController.selectedTypeFilter || "all")
        : "all"
    readonly property bool   _typeFieldVisible: root._activeType === "all"
    readonly property string _fixedTypeValue:   root._activeType === "all" ? "RISK" : root._activeType
    readonly property string _createLabel: {
        switch (root._activeType) {
        case "RISK":   return "New Risk"
        case "ISSUE":  return "New Issue"
        case "CHANGE": return "New Change"
        default:       return "New Entry"
        }
    }
    readonly property bool _createEnabled: root.workspaceController
        ? (root.workspaceController.projectOptions || []).some(function(o) { return String(o.value || "").toLowerCase() !== "all" })
        : false

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (root.detailPage) root.detailPage.scrollToSection(sectionIndex)
    }

    // ── Dialog host ────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            ProjectManagementWidgets.RegisterDialogHost {
                projectOptions:   root.workspaceController ? (root.workspaceController.projectOptions   || []) : []
                typeOptions:      root.workspaceController ? (root.workspaceController.typeOptions      || []) : []
                statusOptions:    root.workspaceController ? (root.workspaceController.statusOptions    || []) : []
                severityOptions:  root.workspaceController ? (root.workspaceController.severityOptions  || []) : []
                typeFieldVisible: root._typeFieldVisible
                fixedTypeValue:   root._fixedTypeValue
                entryLabel:       root._createLabel.replace("New ", "")
                workspaceController: root.workspaceController
                onDeleteRequested: function(entryId) { if (root.workspaceController !== null) root.workspaceController.deleteEntry(entryId) }
            }
        }
    }

    // ── Main layout ────────────────────────────────────────────────────
    Item {
        anchors.fill: parent

        Item {
            anchors.fill: parent
            visible: !root._detailOpen

            Components.RegisterListPage {
                anchors.fill:          parent
                workspaceController:   root.workspaceController
                overviewModel:         root.overviewModel
                entriesModel:          root.entriesModel
                columns:               state.columns
                bulkChangeProperties:  state.bulkChangeProperties
                createLabel:           root._createLabel
                createEnabled:         root._createEnabled
                detailOpen:            root._detailOpen

                onRowActivated:        root._openDetail(0)
                onExportRequested:     { if (root.workspaceController !== null) root.workspaceController.exportRegister() }
                onCreateRequested:     dialogHostLoader.invoke("openCreateDialog")
                onColumnsStateChanged: function(cols) { state.saveColumnState(cols) }
            }
        }

        Loader {
            id: detailPageLoader
            anchors.fill: parent
            active:       root._detailOpen
            visible:      root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent
            AppWidgets.SectionDetailPage {
                open:        true
                anchors.fill: parent
                showHeader:  false
                showEdit:    false
                showDelete:  false
                isBusy:      root.workspaceController ? root.workspaceController.isBusy : false
                sections:    ["Details", "Impact", "Response", "Links"]
                z:           20
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    width:    parent ? parent.width : 0
                    showBack: true
                    title:    root.selectedEntryModel.title    || "Register Entry"
                    subtitle: root.selectedEntryModel.statusLabel || root.selectedEntryModel.subtitle || ""
                    busy:     root.workspaceController ? root.workspaceController.isBusy : false
                    actions:  state.detailActions
                    onBackRequested: root._detailOpen = false
                    onActionTriggered: function(actionId) {
                        if      (actionId === "edit")   dialogHostLoader.invoke("openEditDialog",   root.selectedEntryModel)
                        else if (actionId === "delete") dialogHostLoader.invoke("openDeleteDialog", root.selectedEntryModel)
                    }
                }

                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

                Panels.RegisterDetailPanel {
                    width:           parent ? parent.width : 0
                    detailPage:      detailPageLoader.item
                    entryDetail:     root.selectedEntryModel
                    urgentModel:     root.urgentModel
                    selectedEntryId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                    isBusy:          root.workspaceController ? root.workspaceController.isBusy : false
                    onEditRequested:    dialogHostLoader.invoke("openEditDialog",   root.selectedEntryModel)
                    onDeleteRequested:  dialogHostLoader.invoke("openDeleteDialog", root.selectedEntryModel)
                    onUrgentEntrySelected: function(entryId) { if (root.workspaceController !== null) root.workspaceController.selectEntry(entryId) }
                }
            }
        }
    }
}
