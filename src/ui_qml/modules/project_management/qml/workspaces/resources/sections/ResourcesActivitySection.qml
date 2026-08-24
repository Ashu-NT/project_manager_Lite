pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as PMWidgets

Item {
    id: root

    property string resourceId: ""
    property var workspaceController: null
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property real availableHeight: 0
    property string selectedActivityId: ""

    readonly property var _page: root.workspaceController
        ? root.workspaceController.resourceActivity : ({ "items": [] })

    function _value(model, index) {
        const item = model[index]
        return item ? String(item.value || "all") : "all"
    }

    function _indexForValue(model, value) {
        const expected = String(value || "").toLowerCase()
        for (let index = 0; index < model.length; index += 1) {
            if (String(model[index].value || "").toLowerCase() === expected) return index
        }
        return 0
    }

    function _openSource(item) {
        const state = item ? (item.state || {}) : {}
        if (state.canOpenSource !== true || !root.pmCatalog) return
        const taskId = String(state.taskId || "")
        const projectId = String(state.projectId || "")
        if (taskId.length) root.pmCatalog.pmNavigation.openEntity("tasks", taskId, "activity")
        else if (projectId.length) root.pmCatalog.pmNavigation.openEntity("projects", projectId, "activity")
    }

    function _activityById(itemId) {
        const items = root._page.items || []
        for (let index = 0; index < items.length; index += 1) {
            if (String(items[index].id || "") === String(itemId || "")) return items[index]
        }
        return null
    }

    implicitHeight: Math.max(content.implicitHeight, root.availableHeight)

    Component.onCompleted: {
        if (root.workspaceController) root.workspaceController.loadResourceActivity()
    }
    onResourceIdChanged: {
        root.selectedActivityId = ""
        if (root.workspaceController && root.resourceId.length)
            root.workspaceController.loadResourceActivity()
    }

    ColumnLayout {
        id: content
        width: parent.width
        height: root.implicitHeight
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            showSearch: false
            showFilter: false
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.resourceActivityLoading : false
            onRefreshRequested: {
                if (root.workspaceController) root.workspaceController.refreshResourceActivity()
            }

            AppControls.ComboBox {
                id: categoryFilter
                implicitWidth: 170
                model: [
                    { "value": "all", "label": "All activity" },
                    { "value": "resource", "label": "Resource" },
                    { "value": "capability", "label": "Capability" },
                    { "value": "projects", "label": "Projects" },
                    { "value": "assignments", "label": "Assignments" },
                    { "value": "work", "label": "Work" }
                ]
                textRole: "label"
                currentIndex: root._indexForValue(
                    model,
                    root.workspaceController ? root.workspaceController.resourceActivityCategory : "all"
                )
                onActivated: function(index) {
                    if (root.workspaceController)
                        root.workspaceController.setResourceActivityCategory(root._value(model, index))
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.DateField { id: fromDate; width: 180; placeholderText: "From date" }
            AppControls.DateField { id: toDate; width: 180; placeholderText: "To date" }
            AppControls.SecondaryButton {
                text: "Apply range"
                iconName: "calendar"
                onClicked: {
                    if (root.workspaceController)
                        root.workspaceController.setResourceActivityDateRange(fromDate.text, toDate.text)
                }
            }
        }

        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: root.workspaceController ? root.workspaceController.resourceActivityLoading : false
            message: "Loading authoritative Resource activity..."
            compact: true
            modal: false
        }

        PMWidgets.ActivityLogSection {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 120
            showHeading: false
            showInlineError: false
            showSearch: false
            clientSideSearch: false
            selectedItemId: root.selectedActivityId
            activityModel: ({
                "title": "",
                "subtitle": "",
                "emptyState": "No recorded activity matches these filters.",
                "items": root._page.items || []
            })
            onItemSelected: function(itemId) {
                root.selectedActivityId = itemId
                root._openSource(root._activityById(itemId))
            }
        }

        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            currentPage: root.workspaceController ? root.workspaceController.resourceActivityPage : 1
            pageSize: root.workspaceController ? root.workspaceController.resourceActivityPageSize : 25
            totalItems: root.workspaceController ? root.workspaceController.resourceActivityTotal : 0
            busy: root.workspaceController ? root.workspaceController.resourceActivityLoading : false
            onPageRequested: function(page) { root.workspaceController.setResourceActivityPage(page) }
            onPageSizeRequested: function(size) { root.workspaceController.setResourceActivityPageSize(size) }
        }
    }
}
