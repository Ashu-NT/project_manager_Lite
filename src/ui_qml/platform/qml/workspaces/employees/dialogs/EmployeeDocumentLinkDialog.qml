import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

// "Add Document" -- two distinct operations under one entry point, each
// clearly labeled (never "Add Document" meaning two different things):
//
//   Link Existing Document -- links an already-uploaded Document to this
//   Employee (create_and_link is NOT invoked; only the relationship is
//   created).
//
//   Create New Document -- creates a brand-new Document record, then links
//   it to this Employee in the same user action.
AppWidgets.EntityDialog {
    id: root

    property string employeeId: ""
    property string employeeLabel: ""
    property var documentOptions: []
    property string mode: "existing"
    property string documentCode: ""

    signal linkExistingRequested(string employeeId, string documentId)
    signal createAndLinkRequested(string employeeId, var payload)

    modal: true
    focus: true
    width: Theme.AppTheme.dialogWidthStandard
    title: "Add Document"
    primaryText: root.mode === "existing" ? "Link" : "Create & Link"
    primaryIcon: root.mode === "existing" ? "add" : "add"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function openForEmployee(employeeId, employeeLabel, documentOptions) {
        root.employeeId = employeeId || ""
        root.employeeLabel = employeeLabel || ""
        root.documentOptions = documentOptions || []
        root.mode = "existing"
        _reloadDocumentModel()
        titleField.text = ""
        root.documentCode = ""
        storageUriField.text = ""
        documentTypeCombo.currentIndex = 0
        open()
    }

    function _reloadDocumentModel() {
        documentModel.clear()
        for (let index = 0; index < root.documentOptions.length; index += 1) {
            const option = root.documentOptions[index]
            documentModel.append({ label: option.label || "", value: option.value || "" })
        }
        documentCombo.currentIndex = documentModel.count > 0 ? 0 : -1
    }

    function _currentDocumentId() {
        if (documentCombo.currentIndex < 0 || documentCombo.currentIndex >= documentModel.count) {
            return ""
        }
        return documentModel.get(documentCombo.currentIndex).value || ""
    }

    function submitDialog() {
        if (root.mode === "existing") {
            const documentId = root._currentDocumentId()
            if (documentId.length === 0) {
                root.errorMessage = "Select a document to link."
                return
            }
            root.errorMessage = ""
            root.linkExistingRequested(root.employeeId, documentId)
            return
        }
        if (root.documentCode.trim().length === 0) {
            root.errorMessage = "Document code is required."
            return
        }
        if (titleField.text.trim().length === 0) {
            root.errorMessage = "Document title is required."
            return
        }
        if (storageUriField.text.trim().length === 0) {
            root.errorMessage = "File path or URL is required."
            return
        }
        root.errorMessage = ""
        root.createAndLinkRequested(root.employeeId, {
            documentCode: root.documentCode.trim(),
            title: titleField.text.trim(),
            documentType: documentTypeCombo.currentValue || "GENERAL",
            storageUri: storageUriField.text.trim()
        })
    }

    ListModel { id: documentModel }
    ListModel {
        id: documentTypeModel

        ListElement { label: "General"; value: "GENERAL" }
        ListElement { label: "Manual"; value: "MANUAL" }
        ListElement { label: "Datasheet"; value: "DATASHEET" }
        ListElement { label: "Drawing"; value: "DRAWING" }
        ListElement { label: "Procedure"; value: "PROCEDURE" }
        ListElement { label: "Policy"; value: "POLICY" }
        ListElement { label: "Certificate"; value: "CERTIFICATE" }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Employee"

        AppControls.TextField {
            Layout.fillWidth: true
            readOnly: true
            text: root.employeeLabel
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingSm

        AppControls.SecondaryButton {
            text: "Link Existing Document"
            danger: false
            onClicked: { root.mode = "existing"; root.errorMessage = "" }
        }
        AppControls.SecondaryButton {
            text: "Create New Document"
            danger: false
            onClicked: { root.mode = "new"; root.errorMessage = "" }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        visible: root.mode === "existing"
        label: "Document"
        required: true

        AppControls.ComboBox {
            id: documentCombo
            Layout.fillWidth: true
            model: documentModel
            textRole: "label"
        }
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.mode === "existing" && root.documentOptions.length === 0
        tone: "warning"
        message: "No existing active documents are available to link. Use \"Create New Document\" instead."
    }

    AppWidgets.CodeFieldRow {
        Layout.fillWidth: true
        visible: root.mode === "new"
        label: "Document Code"
        value: root.documentCode
        required: true
        generateVisible: false
        onValueEdited: function(code) { root.documentCode = code }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        visible: root.mode === "new"
        label: "Title"
        required: true

        AppControls.TextField {
            id: titleField
            Layout.fillWidth: true
            placeholderText: "e.g. Employment Contract"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        visible: root.mode === "new"
        label: "Document Type"

        AppControls.ComboBox {
            id: documentTypeCombo
            Layout.fillWidth: true
            model: documentTypeModel
            textRole: "label"
            valueRole: "value"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        visible: root.mode === "new"
        label: "File Path or URL"
        required: true

        AppControls.TextField {
            id: storageUriField
            Layout.fillWidth: true
            placeholderText: "C:/docs/contract.pdf or https://..."
        }
    }
}
