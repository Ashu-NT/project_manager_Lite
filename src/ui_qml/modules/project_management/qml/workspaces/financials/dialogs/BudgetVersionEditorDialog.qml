import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var workspaceController: null
    property string mode: "create"
    property string projectId: ""
    property var budget: null

    signal submitted(
        string mode, string projectId, string budgetId, int rowVersion,
        string name, string currency, string notes
    )

    readonly property bool _isEdit: root.mode === "edit"
    readonly property bool _isSuccessor: root.mode === "successor"
    readonly property var _state: root.budget ? (root.budget.state || {}) : ({})
    readonly property var _currencies: root.workspaceController
        ? (root.workspaceController.currencyOptions || []) : []

    width: 620
    title: root._isEdit ? "Edit Budget Version"
        : (root._isSuccessor ? "Create Budget Successor" : "Create Budget Version")
    subtitle: root._isSuccessor
        ? "Create a draft copied from the approved revision. The predecessor remains unchanged."
        : (root._isEdit
            ? "Only draft metadata can be changed. Currency and revision remain immutable."
            : "Create a governed draft. The server assigns its revision and validates open-version constraints.")
    primaryText: root._isEdit ? "Save Changes"
        : (root._isSuccessor ? "Create Successor" : "Create Version")
    primaryIcon: root._isEdit ? "save" : "add"

    function _currencyIndex(value) {
        const wanted = String(value || "").toUpperCase()
        for (let index = 0; index < root._currencies.length; index += 1) {
            if (String(root._currencies[index].value || "").toUpperCase() === wanted)
                return index
        }
        return 0
    }

    function populate() {
        const title = root.budget ? String(root.budget.title || "") : ""
        nameField.text = root._isEdit
            ? title.replace(/^v\d+\s*-\s*/, "")
            : (root._isSuccessor ? title.replace(/^v\d+\s*-\s*/, "") + " successor" : "")
        notesField.text = root._isEdit ? String(root._state.notes || "") : ""
        const currency = root._isEdit || root._isSuccessor
            ? String(root._state.currency || "")
            : String(root.workspaceController
                ? root.workspaceController.defaultCurrencyCode : "XAF")
        currencyCombo.currentIndex = root._currencyIndex(currency)
        root.errorMessage = ""
        nameField.forceActiveFocus()
    }

    function submitDialog() {
        const name = nameField.text.trim()
        if (!root.projectId) {
            root.errorMessage = "Select a project before creating a Budget version."
            return
        }
        if (!name) {
            root.errorMessage = "Budget name is required."
            nameField.forceActiveFocus()
            return
        }
        const option = root._currencies[currencyCombo.currentIndex] || ({ "value": "XAF" })
        root.errorMessage = ""
        root.submitted(
            root.mode,
            root.projectId,
            String(root.budget ? root.budget.id || "" : ""),
            Number(root._state.rowVersion || 0),
            name,
            String(option.value || "XAF"),
            notesField.text.trim()
        )
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
            label: "Budget name"
            required: true
            AppControls.TextField {
                id: nameField
                Layout.fillWidth: true
                placeholderText: "Approved operating budget"
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Currency"
            required: true
            AppControls.ComboBox {
                id: currencyCombo
                Layout.fillWidth: true
                model: root._currencies
                textRole: "label"
                enabled: !root._isEdit && !root._isSuccessor
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: root._isEdit
            label: "Notes"
            AppControls.TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 88
                wrapMode: TextEdit.WordWrap
            }
        }
    }
}
