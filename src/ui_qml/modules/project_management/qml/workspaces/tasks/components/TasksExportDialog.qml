pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Dialogs
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

FileDialog {
    id: root

    // ── Input properties ─────────────────────────────────────────────────
    property var workspaceController: null
    property var columns: []

    // ── Configuration ────────────────────────────────────────────────────
    title: "Export Tasks"
    fileMode: FileDialog.SaveFile
    nameFilters: ["Excel files (*.xlsx)", "CSV files (*.csv)"]

    onAccepted: {
        if (root.workspaceController !== null) {
            const visibleCols = root.columns.filter(function(c) { 
                return c.visible !== false 
            }).map(function(c) { 
                return { "key": c.key, "label": c.label } 
            })
            root.workspaceController.exportTasks(visibleCols, String(selectedFile || ""))
        }
    }
}
