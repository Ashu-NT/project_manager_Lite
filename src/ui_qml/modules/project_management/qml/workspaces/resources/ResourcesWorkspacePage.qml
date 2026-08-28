pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "components" as Components
import "dialogs" as Dialogs
import "panels" as Panels

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementResourcesWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.resourcesWorkspace
        : null

    // ── State management ──────────────────────────────────────────────────
    ResourcesWorkspaceState {
        id: state
        pmCatalog: root.pmCatalog
        workspaceController: root.workspaceController
    }

    // ── Convenience aliases ────────────────────────────────────────────────
    readonly property var workspaceModel: state.workspaceModel
    readonly property var overviewModel: state.overviewModel
    readonly property var resourcesModel: state.resourcesModel
    readonly property var selectedResourceModel: state.selectedResourceModel
    readonly property var resourceInspectorModel: state.resourceInspectorModel

    // ── Column management ─────────────────────────────────────────────────
    property var _columns: state.columns

    function _saveColumnState(columns) {
        state.saveColumnState(columns)
        root._columns = state.columns
    }

    // ── Detail page state ─────────────────────────────────────────────────
    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property real _detailContentViewportHeight: 0
    property int _pendingDetailSection: 0
    property string _selectedSkillId: ""
    property string _selectedCertificationId: ""
    readonly property var detailPage: detailPageLoader.item
    readonly property string _activeSectionError: {
        if (root.workspaceController === null || root.detailPage === null) return ""
        const errors = root.workspaceController.sectionErrors || {}
        if (root.detailPage.activeSectionIndex === 1) return String(errors.skills || "")
        if (root.detailPage.activeSectionIndex === 2) return String(errors.availability || "")
        if (root.detailPage.activeSectionIndex === 3) return String(errors.projects || "")
        if (root.detailPage.activeSectionIndex === 4) return String(errors.assignments || "")
        if (root.detailPage.activeSectionIndex === 5) return String(errors.activity || "")
        return ""
    }
    readonly property string _visibleDetailError: String(root.workspaceController
        ? root.workspaceController.detailError : "") || root._activeSectionError
    readonly property var _detailActions: {
        const idx = detailPage ? detailPage.activeSectionIndex : 0
        return state.detailActionsForSection(idx, {
            "selectedSkillId": root._selectedSkillId,
            "selectedCertificationId": root._selectedCertificationId
        })
    }
    readonly property bool _hasInspector: String(root.workspaceController
        ? root.workspaceController.selectedResourceId : "").length > 0
    readonly property int _sideInspectorThreshold: Theme.AppTheme.inspectorWidth + 720
    readonly property bool _useSideInspector: root.width >= root._sideInspectorThreshold
    readonly property var _inspectorSections: root.resourceInspectorModel.fields || []

    function _clearInspector() {
        compactInspector.close()
        if (root.workspaceController !== null) root.workspaceController.selectResource("")
        Qt.callLater(listPage.restoreTableFocus)
    }

    function _openSelectedResource() {
        if (root.workspaceController === null || !root._hasInspector) return
        if (root.workspaceController.activateResource(String(root.resourceInspectorModel.id || ""))) {
            compactInspector.close()
            root._openDetail(0)
        }
    }

    on_UseSideInspectorChanged: {
        if (root._useSideInspector) compactInspector.close()
        else if (root._hasInspector && !root._detailOpen) compactInspector.open()
    }
    on_HasInspectorChanged: {
        if (!root._hasInspector) compactInspector.close()
        else if (!root._useSideInspector && !root._detailOpen) compactInspector.open()
    }

    function _openDetail(sectionIndex) {
        compactInspector.close()
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (detailPage) detailPage.scrollToSection(sectionIndex)
    }

    function _rowById(rows, rowId) {
        const source = rows || []
        for (let i = 0; i < source.length; i++) {
            if (String(source[i].id || "") === String(rowId || "")) return source[i]
        }
        return null
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.ResourcesDialogHost {
                workerTypeOptions: root.workspaceController ? (root.workspaceController.workerTypeOptions || []) : []
                kindOptions: root.workspaceController ? (root.workspaceController.kindOptions || []) : []
                categoryOptions: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                employeeOptions: root.workspaceController ? (root.workspaceController.employeeOptions || []) : []
                departmentOptions: root.workspaceController ? (root.workspaceController.departmentOptions || []) : []
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                workspaceController: root.workspaceController

                onDeactivateRequested: function(resourceId, expectedVersion) {
                    if (root.workspaceController !== null)
                        root.workspaceController.deactivateResource(resourceId, expectedVersion)
                }
                onReactivateRequested: function(resourceId, expectedVersion) {
                    if (root.workspaceController !== null)
                        root.workspaceController.reactivateResource(resourceId, expectedVersion)
                }
            }
        }
    }

    FileDialog {
        id: _exportDialog
        title: "Export Resources"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Excel files (*.xlsx)", "CSV files (*.csv)"]
        onAccepted: {
            if (root.workspaceController !== null) {
                const cols = state.columns.filter(function(c) { return c.visible !== false })
                    .map(function(c) { return { "key": c.key, "label": c.label } })
                root.workspaceController.exportResources(cols, String(selectedFile || ""))
            }
        }
    }

    // ── Stacked layout: list page / detail page ───────────────────
    Item {
        anchors.fill: parent

        // ── List page ─────────────────────────────────────────────────────
        RowLayout {
            id: _listPage
            anchors.fill: parent
            visible: !root._detailOpen
            spacing: 0

            Components.ResourcesListPage {
                id: listPage
                objectName: "resourcesCatalogListPage"
                Layout.fillWidth: true
                Layout.fillHeight: true
                workspaceController: root.workspaceController
                state: state
                overviewModel: root.overviewModel
                resourcesModel: root.resourcesModel

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectResource(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null
                            && root.workspaceController.activateResource(rowId)) {
                        root._openDetail(0)
                    }
                }
                onColumnsStateChanged: function(columns) {
                    if (root.workspaceController !== null) root._saveColumnState(columns)
                }
                onSearchChanged: function(text) {
                    if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                }
                onFilterClicked: filterPopup.open()
                onRefreshRequested: {
                    if (root.workspaceController !== null) root.workspaceController.refresh()
                }
                onExportRequested: _exportDialog.open()
                onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
            }

            AppWidgets.InspectorPanel {
                Layout.fillHeight: true
                Layout.preferredWidth: Theme.AppTheme.inspectorWidth
                visible: root._hasInspector && root._useSideInspector
                title: root.resourceInspectorModel.title || "Resource"
                statusLabel: root.resourceInspectorModel.statusLabel || ""
                sections: root._inspectorSections
                busy: root.workspaceController ? root.workspaceController.inspectorLoading : false
                editActionLabel: "Open Resource"
                showEditAction: (root.resourceInspectorModel.state || {}).canRead === true
                onCloseRequested: root._clearInspector()
                onEditRequested: root._openSelectedResource()

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.inspectorError : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.inspectorError : ""
                }
            }

            Components.ResourcesFilterPopup {
                id: filterPopup
                workspaceController: root.workspaceController
                state: state
                onClosed: Qt.callLater(listPage.restoreTableFocus)
            }

        }

        Popup {
            id: compactInspector
            parent: root
            x: Math.max(0, root.width - width)
            y: 0
            width: Math.min(Theme.AppTheme.inspectorWidth, root.width * 0.9)
            height: root.height
            padding: 0
            modal: false
            closePolicy: Popup.NoAutoClose

            contentItem: AppWidgets.InspectorPanel {
                title: root.resourceInspectorModel.title || "Resource"
                statusLabel: root.resourceInspectorModel.statusLabel || ""
                sections: root._inspectorSections
                busy: root.workspaceController ? root.workspaceController.inspectorLoading : false
                editActionLabel: "Open Resource"
                showEditAction: (root.resourceInspectorModel.state || {}).canRead === true
                onCloseRequested: root._clearInspector()
                onEditRequested: root._openSelectedResource()

                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: String(root.workspaceController ? root.workspaceController.inspectorError : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.inspectorError : ""
                }
            }
        }

        Connections {
            target: root.workspaceController
            function onSelectedResourceIdChanged() {
                if (!root._useSideInspector && root._hasInspector && !root._detailOpen)
                    compactInspector.open()
                else if (!root._hasInspector || root._useSideInspector)
                    compactInspector.close()
            }
        }

        // ── Detail page (covers full area, z:20) ──────────────────────────
        Loader {
            id: detailPageLoader
            anchors.fill: parent
            active: root._detailOpen
            visible: root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open: true
                anchors.fill: parent
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: state.detailSections
                contentBottomPadding: activeSectionIndex >= 3 ? 0 : Theme.AppTheme.pagePadding
                z: 20
                onContentViewportHeightChanged: {
                    root._detailContentViewportHeight = contentViewportHeight
                }
                Component.onCompleted: {
                    root._detailContentViewportHeight = contentViewportHeight
                    scrollToSection(root._pendingDetailSection)
                }

                onSectionChanged: function(index) {
                    if (index === 1 && root.workspaceController !== null) {
                        root.workspaceController.loadSkillsAndCerts(
                            root.workspaceController.selectedResourceId
                        )
                    } else if (index === 3 && root.workspaceController !== null) {
                        root.workspaceController.loadResourceProjects()
                    } else if (index === 4 && root.workspaceController !== null) {
                        root.workspaceController.loadResourceAssignments()
                    } else if (index === 5 && root.workspaceController !== null) {
                        root.workspaceController.loadResourceActivity()
                    }
                }

                AppWidgets.ContextualActionToolbar {
                    detailPagePinned: true
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedResourceModel.title || "Resource Details"
                    subtitle: root.selectedResourceModel.statusLabel || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: {
                        root._selectedSkillId = ""
                        root._selectedCertificationId = ""
                        root._detailOpen = false
                    }
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") {
                            dialogHostLoader.invoke("openEditDialog", root.selectedResourceModel)
                        } else if (actionId === "lifecycle") {
                            dialogHostLoader.invoke("openLifecycleDialog", root.selectedResourceModel)
                        } else if (actionId === "remove_skill") {
                            const skill = root._rowById(root.workspaceController ? root.workspaceController.resourceSkills : [], root._selectedSkillId)
                            if (root.workspaceController !== null && skill !== null) {
                                root.workspaceController.removeSkill(root._selectedSkillId, Number(skill.version || 0))
                            }
                        } else if (actionId === "edit_skill") {
                            const skill = root._rowById(root.workspaceController ? root.workspaceController.resourceSkills : [], root._selectedSkillId)
                            if (skill !== null) dialogHostLoader.invoke("openEditSkillDialog", skill)
                        } else if (actionId === "remove_certification") {
                            const certification = root._rowById(root.workspaceController ? root.workspaceController.resourceCertifications : [], root._selectedCertificationId)
                            if (root.workspaceController !== null && certification !== null) {
                                root.workspaceController.removeCertification(root._selectedCertificationId, Number(certification.version || 0))
                            }
                        } else if (actionId === "edit_certification") {
                            const certification = root._rowById(root.workspaceController ? root.workspaceController.resourceCertifications : [], root._selectedCertificationId)
                            if (certification !== null) dialogHostLoader.invoke("openEditCertificationDialog", certification)
                        }
                    }
                }

                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: root._detailOpen
                        && root._visibleDetailError.length > 0
                    tone: "danger"
                    message: root._visibleDetailError
                }
                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && root._visibleDetailError.length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Panels.ResourcesDetailPanel {
                    id: resourcesDetailPanel
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    resourceDetail: root.selectedResourceModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    workspaceController: root.workspaceController
                    pmCatalog: root.pmCatalog
                    availableHeight: Math.max(0, root._detailContentViewportHeight - y)
                    canManageSkills: root.pmCatalog ? root.pmCatalog.pmCapabilityController.canManageSkills : false
                    onSkillSelectionChanged: function(skillId) {
                        root._selectedSkillId = String(skillId || "")
                    }
                    onCertificationSelectionChanged: function(certId) {
                        root._selectedCertificationId = String(certId || "")
                    }
                    onAddSkillRequested: dialogHostLoader.invoke("openAddSkillDialog")
                    onAddCertificationRequested: dialogHostLoader.invoke("openAddCertificationDialog")
                    onRemoveSkillRequested: function(skillId) {
                        const skill = root._rowById(root.workspaceController ? root.workspaceController.resourceSkills : [], skillId)
                        if (root.workspaceController !== null && skill !== null)
                            root.workspaceController.removeSkill(skillId, Number(skill.version || 0))
                    }
                    onRemoveCertificationRequested: function(certId) {
                        const certification = root._rowById(root.workspaceController ? root.workspaceController.resourceCertifications : [], certId)
                        if (root.workspaceController !== null && certification !== null)
                            root.workspaceController.removeCertification(certId, Number(certification.version || 0))
                    }
                }
            }
        }
    }
}
