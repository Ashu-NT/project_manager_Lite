import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property string projectId: ""
    property var change: null
    signal submitted(var payload)

    readonly property bool _editing: root.mode === "edit"
    readonly property var _state: root.change ? (root.change.state || {}) : ({})

    width: 640
    title: root._editing ? "Edit Change Request" : "Create Change Request"
    subtitle: "The server snapshots current approved Budget and Forecast bases."
    primaryText: root._editing ? "Save Changes" : "Create Request"
    primaryIcon: root._editing ? "save" : "add"

    function populate() {
        titleField.text = root._editing ? String(root.change.title || "") : ""
        reasonField.text = root._editing ? String(root._state.reason || "") : ""
        descriptionField.text = root._editing ? String(root._state.description || "") : ""
        effectiveDateField.text = root._editing
            ? String(root._state.effectiveDate || "")
            : Qt.formatDate(new Date(), "yyyy-MM-dd")
        root.errorMessage = ""
        titleField.forceActiveFocus()
    }

    function submitDialog() {
        if (!titleField.text.trim()) {
            root.errorMessage = "Change title is required."
            titleField.forceActiveFocus()
            return
        }
        if (!reasonField.text.trim()) {
            root.errorMessage = "Change reason is required."
            reasonField.forceActiveFocus()
            return
        }
        if (!effectiveDateField.text.trim()) {
            root.errorMessage = "Effective date is required."
            effectiveDateField.forceActiveFocus()
            return
        }
        root.errorMessage = ""
        root.submitted({
            "projectId": root.projectId,
            "changeId": root.change ? String(root.change.id || "") : "",
            "rowVersion": Number(root._state.version || 0),
            "title": titleField.text.trim(),
            "reason": reasonField.text.trim(),
            "description": descriptionField.text.trim(),
            "effectiveDate": effectiveDateField.text.trim()
        })
    }

    onOpened: root.populate()
    onRejected: root.close()

    GridLayout {
        Layout.fillWidth: true
        columns: width >= 520 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            Layout.columnSpan: parent.columns
            label: "Title"
            required: true
            AppControls.TextField {
                id: titleField
                Layout.fillWidth: true
                placeholderText: "Approved scope or commercial change"
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Reason"
            required: true
            AppControls.TextField {
                id: reasonField
                Layout.fillWidth: true
                placeholderText: "Client request, risk response, or correction"
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Effective date"
            required: true
            AppControls.DateField {
                id: effectiveDateField
                Layout.fillWidth: true
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            Layout.columnSpan: parent.columns
            label: "Description"
            AppControls.TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 96
                wrapMode: TextEdit.WordWrap
                placeholderText: "Describe the governed change and expected outcome."
            }
        }
    }
}
