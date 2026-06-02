pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property string selectedProjectId: ""
    property var selectedActivityData: ({})
    property var workspaceController: null

    signal createBaselineRequested(var payload)

    function openCreateBaselineDialog() {
        baselineNameField.text = ""
        createBaselineDialog.errorMessage = ""
        createBaselineDialog.open()
    }

    function _handleResult(dialog, result) {
        if (!result || result.ok === false) {
            dialog.errorMessage = String((result && (result.error || result.message)) || "Operation failed. Please try again.")
        } else {
            dialog.errorMessage = ""
            dialog.close()
        }
    }

    AppWidgets.EntityDialog {
        id: createBaselineDialog
        title:       "Save Baseline"
        subtitle:    "Create a controlled schedule snapshot for comparison and governance."
        primaryText: "Save Baseline"
        primaryIcon: "register"
        primaryEnabled: String(root.selectedProjectId || "").length > 0
        width: 420

        onAccepted: {
            const result = root.workspaceController
                ? root.workspaceController.createBaseline({
                      "projectId": root.selectedProjectId,
                      "name": baselineNameField.text
                  })
                : null
            if (result === null && !root.workspaceController) {
                root.createBaselineRequested({
                    "projectId": root.selectedProjectId,
                    "name": baselineNameField.text
                })
                createBaselineDialog.close()
            } else {
                root._handleResult(createBaselineDialog, result)
            }
        }
        onRejected: createBaselineDialog.close()

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Baseline Name"

            AppControls.TextField {
                id: baselineNameField
                Layout.fillWidth: true
                placeholderText: "e.g. Approved Plan v1"
            }
        }
    }

}

