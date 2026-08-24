pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property var sectionErrors: ({})
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property var projectDetail: ({ "id": "" })
    property var projectResourcesModel: ({
        "title": "Resources", "subtitle": "", "emptyState": "Open this section to load project resources.", "items": []
    })
    property var projectResourcesTableModel: null
    property var assignableResourceOptions: []
    property string selectedProjectResourceId: ""
    property bool isBusy: false
    property real availableHeight: 0

    readonly property bool _hasProject: String(root.projectDetail.id || "").length > 0
    readonly property int _resourceCount: (root.projectResourcesModel.items || []).length
    readonly property int _tableHeight: Math.max(
        120,
        Theme.AppTheme.normalRowHeight
            + Math.max(root._resourceCount, 1) * Theme.AppTheme.compactRowHeight
            + 1
    )

    function openEditSelected() {
        if (root.selectedProjectResourceId.length > 0) {
            _editPopup.openForSelected()
        }
    }

    function confirmRemoveSelected() {
        if (root.selectedProjectResourceId.length > 0) {
            _deleteConfirm.open()
        }
    }

    implicitHeight: Math.max(_col.implicitHeight, root.availableHeight)

    ColumnLayout {
        id: _col
        width: parent.width
        height: root.implicitHeight
        spacing: 0

        Component.onCompleted: {
            const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
            if (ctrl) ctrl.loadAssignableResources()
        }

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: String(root.projectResourcesModel.searchText || "")
            searchPlaceholder: "Search resource, code, or role..."
            showFilter: false
            showRefresh: true
            isBusy: root.isBusy
            onSearchChanged: function(text) {
                const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                if (ctrl) ctrl.setProjectResourcesSearch(text)
            }
            onRefreshRequested: {
                const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                if (ctrl) ctrl.loadProjectResources()
            }
            AppControls.ComboBox {
                implicitWidth: 125
                textRole: "label"
                model: [{"value":"all","label":"All staffing"},{"value":"active","label":"Active"},{"value":"inactive","label":"Inactive"}]
                onActivated: function(index) {
                    const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                    if (ctrl) ctrl.setProjectResourcesActive(String(model[index].value))
                }
            }
        }

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Resources"
            subtitle: root._resourceCount > 0 ? String(root._resourceCount) : ""
            busy: root.isBusy
            createLabel: root._hasProject ? "Assign Resource" : ""
            actions: []
            onCreateRequested: _assignPopup.open()
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.sectionErrors["resources"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["resources"] || "")
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: root._tableHeight + resourcePagination.implicitHeight

            AppWidgets.DataTable {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: resourcePagination.top
                columns: [
                    { key: "resourceName",   label: "Resource",      flex: 2, sortable: true },
                    { key: "resourceCode",   label: "Code",          flex: 0, minWidth: 90, sortable: true },
                    { key: "role",           label: "Role",          flex: 1.2, sortable: true },
                    { key: "plannedHours",   label: "Project Plan",  flex: 0, minWidth: 105, sortable: true },
                    { key: "allocatedHours", label: "To Tasks",      flex: 0, minWidth: 95, sortable: true },
                    { key: "actualHours",    label: "Actual",        flex: 0, minWidth: 85, sortable: true },
                    { key: "remainingHours", label: "Remaining",     flex: 0, minWidth: 95, sortable: true },
                    { key: "statusLabel",    label: "Status",        flex: 0, minWidth: 90, type: "status" }
                ]
                sourceModel: root.projectResourcesTableModel
                sortingMode: "server"
                sortKey: String(root.projectResourcesModel.sortKey || "resourceName")
                sortDirection: root.projectResourcesModel.sortDirection === "desc" ? Qt.DescendingOrder : Qt.AscendingOrder
                selectedRowId: root.selectedProjectResourceId
                loading: root.isBusy
                emptyText: root.projectResourcesModel.emptyState || "No resources allocated to this project."
                onRowSelected: function(rowId) {
                    const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                    if (ctrl) ctrl.selectProjectResource(rowId)
                }
                onSortRequested: function(key, direction) {
                    const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                    if (ctrl) ctrl.setProjectResourcesSort(key, direction)
                }
            }

            AppWidgets.TablePaginationBar {
                id: resourcePagination
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: Number(root.projectResourcesModel.page || 1)
                pageSize: Number(root.projectResourcesModel.pageSize || 25)
                totalItems: Number(root.projectResourcesModel.total || 0)
                busy: root.isBusy
                onPageRequested: function(page) { root.pmCatalog.projectsWorkspace.setProjectResourcesPage(page) }
                onPageSizeRequested: function(size) { root.pmCatalog.projectsWorkspace.setProjectResourcesPageSize(size) }
            }
        }

        AppWidgets.EntityDialog {
            id: _editPopup
            title: "Edit Resource Assignment"

            property var _rowState: ({})
            property var _usage: ({})

            function openForSelected() {
                const items = root.projectResourcesModel.items || []
                const selId = root.selectedProjectResourceId
                _rowState = {}
                for (let i = 0; i < items.length; i++) {
                    if (String(items[i].id || "") === selId) {
                        _rowState = items[i].state || {}
                        break
                    }
                }
                _editHoursField.text = String(_rowState.plannedHours || "0")
                _editRateField.text = String(_rowState.hourlyRate || "")
                _editActiveToggle.checked = Boolean(_rowState.isActive !== false)
                _editError.message = ""
                _usage = {}
                const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                if (ctrl && selId.length > 0) {
                    _usage = ctrl.getProjectResourceUsage(selId) || {}
                }
                open()
            }

            contentItem: ColumnLayout {
                spacing: Theme.AppTheme.spacingSm
                implicitWidth: 320

                AppWidgets.FormField {
                    Layout.fillWidth: true
                    label: "Project planned hours"
                    helperText: "Total planned work for this resource across this project."

                    AppControls.TextField {
                        id: _editHoursField
                        Layout.fillWidth: true
                        placeholderText: "0"
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                        enabled: !(root.pmCatalog ? root.pmCatalog.projectsWorkspace.isBusy : false)
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    visible: Object.keys(_editPopup._usage).length > 0

                    // Terminology matches Task Assignment's Project Resource
                    // Context exactly (docs §44 follow-up §47) -- the same
                    // backend facts must never read as different labels in
                    // different places.
                    AppControls.Label {
                        text: "Project planned hours: " + String(_editPopup._usage.plannedHoursLabel || "0.0 h")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                    AppControls.Label {
                        text: "Distributed to tasks: " + String(_editPopup._usage.allocatedToTasksHoursLabel || "0.0 h")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                    AppControls.Label {
                        text: "Unallocated: " + String(_editPopup._usage.unallocatedPlannedHoursLabel || "0.0 h")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                    AppControls.Label {
                        text: "Actual worked: " + String(_editPopup._usage.actualHoursLabel || "0.0 h")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                    AppControls.Label {
                        text: "Remaining vs plan: " + String(_editPopup._usage.remainingProjectHoursLabel || "0.0 h")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                }

                AppControls.Label {
                    text: "Hourly Rate"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.TextField {
                    id: _editRateField
                    Layout.fillWidth: true
                    placeholderText: "0.00"
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    enabled: !(root.pmCatalog ? root.pmCatalog.projectsWorkspace.isBusy : false)
                }

                AppControls.CheckBox {
                    id: _editActiveToggle
                    text: "Active"
                    checked: true
                    enabled: !(root.pmCatalog ? root.pmCatalog.projectsWorkspace.isBusy : false)
                }

                AppWidgets.InlineMessage {
                    id: _editError
                    Layout.fillWidth: true
                    tone: "danger"
                    actionLabel: _editError.message.indexOf("updated by another user") >= 0 ? "Refresh" : ""
                    onActionClicked: _editPopup.openForSelected()
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.SecondaryButton {
                        Layout.fillWidth: true
                        text: "Cancel"
                        onClicked: _editPopup.close()
                        enabled: !(root.pmCatalog ? root.pmCatalog.projectsWorkspace.isBusy : false)
                    }

                    AppControls.PrimaryButton {
                        Layout.fillWidth: true
                        text: "Save"
                        iconName: "approve"
                        enabled: !(root.pmCatalog ? root.pmCatalog.projectsWorkspace.isBusy : false)
                        onClicked: {
                            const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                            if (!ctrl) return
                            _editError.message = ""
                            const result = ctrl.updateProjectResource({
                                "projectResourceId": String(_editPopup._rowState.projectResourceId || ""),
                                "plannedHours": _editHoursField.text || "0",
                                "hourlyRate": _editRateField.text || "",
                                "isActive": _editActiveToggle.checked,
                                "version": _editPopup._rowState.version !== undefined ? String(_editPopup._rowState.version) : ""
                            })
                            if (result && result.ok === false) {
                                const message = String(result.error || "Update failed.")
                                _editError.message = message.indexOf("STALE_WRITE") >= 0 || message.indexOf("updated by another user") >= 0
                                    ? "This resource plan was updated by another user. Refresh the latest values before saving again."
                                    : message
                            } else {
                                _editPopup.close()
                            }
                        }
                    }
                }
            }
        }

        AppControls.ConfirmationDialog {
            id: _deleteConfirm
            title: "Remove Resource"
            message: "Remove this resource from the project? This cannot be undone. If the " +
                "resource has recorded actual time on this project's tasks, removal will be blocked " +
                "and you should deactivate it instead."
            confirmLabel: "Remove"
            confirmDanger: true
            onConfirmed: {
                const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                if (!ctrl) return
                const result = ctrl.removeProjectResource(root.selectedProjectResourceId)
                if (result && result.ok === false) {
                    root.sectionErrors = Object.assign({}, root.sectionErrors, { "resources": String(result.error || "Removal failed.") })
                }
            }
        }

        AppWidgets.EntityDialog {
            id: _assignPopup
            title: "Assign Resource"

            onOpened: {
                _resourceCombo.currentIndex = -1
                _hoursField.text = ""
                _rateField.text = ""
                _assignError.message = ""
            }

            contentItem: ColumnLayout {
                spacing: Theme.AppTheme.spacingSm
                implicitWidth: 360

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Resource"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.ComboBox {
                    id: _resourceCombo
                    Layout.fillWidth: true
                    model: root.assignableResourceOptions
                    textRole: "label"
                    placeholderText: (root.assignableResourceOptions || []).length === 0
                        ? "No resources available to assign"
                        : "Select a resource..."
                    enabled: (root.assignableResourceOptions || []).length > 0
                        && !(root.pmCatalog ? root.pmCatalog.projectsWorkspace.isBusy : false)
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        AppControls.Label {
                            text: "Planned Hours"
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }

                        AppControls.TextField {
                            id: _hoursField
                            Layout.fillWidth: true
                            placeholderText: "0"
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            enabled: !(root.pmCatalog ? root.pmCatalog.projectsWorkspace.isBusy : false)
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        AppControls.Label {
                            text: "Hourly Rate (optional)"
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }

                        AppControls.TextField {
                            id: _rateField
                            Layout.fillWidth: true
                            placeholderText: "0.00"
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            enabled: !(root.pmCatalog ? root.pmCatalog.projectsWorkspace.isBusy : false)
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    id: _assignError
                    Layout.fillWidth: true
                    tone: "danger"
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.SecondaryButton {
                        Layout.fillWidth: true
                        text: "Cancel"
                        onClicked: _assignPopup.close()
                        enabled: !(root.pmCatalog ? root.pmCatalog.projectsWorkspace.isBusy : false)
                    }

                    AppControls.PrimaryButton {
                        Layout.fillWidth: true
                        text: "Assign"
                        iconName: "add"
                        enabled: _resourceCombo.currentIndex >= 0
                            && !(root.pmCatalog ? root.pmCatalog.projectsWorkspace.isBusy : false)
                        onClicked: {
                            const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                            if (!ctrl) return
                            const options = root.assignableResourceOptions || []
                            const selected = options[_resourceCombo.currentIndex]
                            if (!selected) return
                            _assignError.message = ""
                            const result = ctrl.assignProjectResource({
                                "resourceId": String(selected.value || ""),
                                "plannedHours": _hoursField.text || "0",
                                "hourlyRate": _rateField.text || ""
                            })
                            if (result && result.ok === false) {
                                _assignError.message = String(result.error || "Assignment failed.")
                            } else {
                                _assignPopup.close()
                            }
                        }
                    }
                }
            }
        }
    }
}
