pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property string selectedProjectId: ""
    property var selectedActivityData: ({})

    signal createBaselineRequested(var payload)

    function openCreateBaselineDialog() {
        baselineNameField.text = ""
        createBaselineDialog.open()
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
            root.createBaselineRequested({
                "projectId": root.selectedProjectId,
                "name": baselineNameField.text
            })
            createBaselineDialog.close()
        }
        onRejected: createBaselineDialog.close()

        AppControls.TextField {
            id: baselineNameField
            Layout.fillWidth: true
            placeholderText: "Baseline name"
        }
    }

}

