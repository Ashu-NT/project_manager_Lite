pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property string resourceId: ""
    property var workspaceController: null
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog

    readonly property var _page: root.workspaceController
        ? root.workspaceController.resourceActivity : ({ "items": [] })

    function _value(model, index) {
        const item = model[index]
        return item ? String(item.value || "all") : "all"
    }

    function _openSource(item) {
        const state = item ? (item.state || {}) : {}
        if (state.canOpenSource !== true || !root.pmCatalog) return
        const taskId = String(state.taskId || "")
        const projectId = String(state.projectId || "")
        if (taskId.length) root.pmCatalog.pmNavigation.openEntity("tasks", taskId, "activity")
        else if (projectId.length) root.pmCatalog.pmNavigation.openEntity("projects", projectId, "activity")
    }

    implicitHeight: content.implicitHeight

    Component.onCompleted: {
        if (root.workspaceController) root.workspaceController.loadResourceActivity()
    }
    onResourceIdChanged: {
        if (root.workspaceController && root.resourceId.length)
            root.workspaceController.loadResourceActivity()
    }

    ColumnLayout {
        id: content
        width: parent.width
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            showSearch: false
            showFilter: false
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.resourceActivityLoading : false
            onRefreshRequested: {
                if (root.workspaceController) root.workspaceController.loadResourceActivity()
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

        AppWidgets.ActivityFeed {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(120, implicitHeight)
            items: root._page.items || []
            emptyText: "No recorded activity matches these filters."
            onItemActivated: function(item) { root._openSource(item) }
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
