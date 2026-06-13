pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
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

    readonly property bool _hasProject: String(root.projectDetail.id || "").length > 0
    readonly property int _resourceCount: (root.projectResourcesModel.items || []).length

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

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        Component.onCompleted: {
            const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
            if (ctrl) ctrl.loadAssignableResources()
        }

        AppWidgets.ContextualActionToolbar {
            width: parent.width
            title: "Resources"
            subtitle: root._resourceCount > 0 ? String(root._resourceCount) : ""
            busy: root.isBusy
            createLabel: root._hasProject ? "Assign Resource" : ""
            actions: []
            onCreateRequested: _assignPopup.open()
        }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors["resources"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["resources"] || "")
        }

        AppWidgets.DataTable {
            width: parent.width
            height: Math.min(360, Math.max(200, implicitHeight))
            columns: [
                { key: "title",          label: "Resource",      flex: 2, sortable: true },
                { key: "subtitle",       label: "Role",          flex: 1.5 },
                { key: "supportingText", label: "Planned Hours", flex: 1, minWidth: 100 },
                { key: "metaText",       label: "Hourly Rate",   flex: 1, minWidth: 100 },
                { key: "statusLabel",    label: "Status",        flex: 0, minWidth: 90, type: "status" }
            ]
            sourceModel: root.projectResourcesTableModel
            selectedRowId: root.selectedProjectResourceId
            loading: root.isBusy
            emptyText: root.projectResourcesModel.emptyState || "No resources allocated to this project."
            onRowSelected: function(rowId) {
                const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                if (ctrl) ctrl.selectProjectResource(rowId)
            }
        }

        AppWidgets.EntityDialog {
            id: _editPopup
            title: "Edit Resource Assignment"

            property var _rowState: ({})

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
                open()
            }

            contentItem: ColumnLayout {
                spacing: Theme.AppTheme.spacingSm
                implicitWidth: 320

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
                            id: _editHoursField
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
                    }
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
                                "isActive": _editActiveToggle.checked
                            })
                            if (result && result.ok === false) {
                                _editError.message = String(result.error || "Update failed.")
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
            message: "Remove this resource from the project? This cannot be undone."
            confirmLabel: "Remove"
            confirmDanger: true
            onConfirmed: {
                const ctrl = root.pmCatalog ? root.pmCatalog.projectsWorkspace : null
                if (ctrl) ctrl.removeProjectResource(root.selectedProjectResourceId)
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
