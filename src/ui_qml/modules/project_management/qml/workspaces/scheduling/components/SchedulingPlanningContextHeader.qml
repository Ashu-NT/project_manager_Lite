pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import workspaces.scheduling.components 1.0

Item {
    id: root

    property ProjectManagementControllers.ProjectManagementSchedulingWorkspaceController workspaceController: null

    implicitHeight: actionBar.implicitHeight

    function _optionIndexForValue(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return -1
    }

    SchedulingActionBar {
        id: actionBar
        anchors.fill: parent
        isBusy: root.workspaceController ? root.workspaceController.isBusy : false
        actions: [
            { "id": "refresh", "label": "Refresh", "icon": "refresh", "enabled": true },
            { "id": "run_cpm", "label": "Run CPM", "icon": "approve",
              "enabled": String(root.workspaceController ? root.workspaceController.selectedProjectId : "").length > 0 }
        ]

        AppControls.ComboBox {
            Layout.preferredWidth: 210
            model:      root.workspaceController ? (root.workspaceController.projectOptions || []) : []
            textRole:   "label"
            enabled:    !(root.workspaceController ? root.workspaceController.isBusy : false)
            currentIndex: root._optionIndexForValue(
                root.workspaceController ? (root.workspaceController.projectOptions || []) : [],
                root.workspaceController ? root.workspaceController.selectedProjectId : ""
            )
            onActivated: function(index) {
                const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                if (root.workspaceController !== null && opts[index])
                    root.workspaceController.selectProject(String(opts[index].value || ""))
            }
        }

        onActionTriggered: function(actionId) {
            if (root.workspaceController === null) return
            if      (actionId === "refresh") root.workspaceController.refresh()
            else if (actionId === "run_cpm") root.workspaceController.recalculateSchedule()
        }
    }
}
