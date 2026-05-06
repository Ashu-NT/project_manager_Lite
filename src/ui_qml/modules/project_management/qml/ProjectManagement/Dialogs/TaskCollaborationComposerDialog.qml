import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property var taskData: ({})
    property var mentionOptions: []
    property var documentOptions: []
    property var pendingAttachments: []
    property var pendingDocuments: []

    signal submitted(var payload)

    modal: true
    width: 640
    height: Math.min(720, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 720)
    title: "Post Task Update"
    closePolicy: Popup.CloseOnEscape

    function selectedTaskState() {
        return root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
    }

    function localPathFromUrl(urlValue) {
        const raw = String(urlValue || "")
        if (!raw) {
            return ""
        }
        if (raw.indexOf("file:///") === 0) {
            return decodeURIComponent(raw.slice(8))
        }
        if (raw.indexOf("file://") === 0) {
            return decodeURIComponent(raw.slice(7))
        }
        return decodeURIComponent(raw)
    }

    function resetDraft() {
        commentArea.text = ""
        mentionCombo.currentIndex = 0
        documentCombo.currentIndex = 0
        root.pendingAttachments = []
        root.pendingDocuments = []
    }

    function optionAt(options, index) {
        if (!options || index < 0 || index >= options.length) {
            return {}
        }
        return options[index] || {}
    }

    function insertSelectedMention() {
        const option = root.optionAt(root.mentionOptions || [], mentionCombo.currentIndex)
        const handle = String(option.value || "")
        if (!handle) {
            return
        }
        const cursor = commentArea.cursorPosition
        const prefix = cursor > 0 && !/\s/.test(commentArea.text.charAt(cursor - 1)) ? " " : ""
        commentArea.insert(cursor, prefix + "@" + handle + " ")
        commentArea.forceActiveFocus()
    }

    function queueSelectedDocument() {
        const option = root.optionAt(root.documentOptions || [], documentCombo.currentIndex)
        const documentId = String(option.value || "")
        const label = String(option.label || "")
        if (!documentId) {
            return
        }
        for (let index = 0; index < root.pendingDocuments.length; index += 1) {
            if (String(root.pendingDocuments[index].id || "") === documentId) {
                return
            }
        }
        root.pendingDocuments = root.pendingDocuments.concat([{ "id": documentId, "label": label }])
    }

    function buildPayload() {
        const state = root.selectedTaskState()
        return {
            "taskId": String(state.taskId || state.id || ""),
            "body": commentArea.text,
            "attachments": root.pendingAttachments.slice(),
            "linkedDocumentIds": root.pendingDocuments.map(function(item) { return String(item.id || "") })
        }
    }

    onOpened: root.resetDraft()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
    }

    FileDialog {
        id: attachmentDialog

        fileMode: FileDialog.OpenFiles
        title: "Attach File"

        onAccepted: {
            const additions = []
            for (let index = 0; index < selectedFiles.length; index += 1) {
                const localPath = root.localPathFromUrl(selectedFiles[index])
                if (localPath.length > 0 && root.pendingAttachments.indexOf(localPath) === -1) {
                    additions.push(localPath)
                }
            }
            if (additions.length > 0) {
                root.pendingAttachments = root.pendingAttachments.concat(additions)
            }
        }
    }

    contentItem: Flickable {
        id: dialogFlickable

        contentWidth: width
        contentHeight: formLayout.implicitHeight
        clip: true

        ColumnLayout {
            id: formLayout

            width: dialogFlickable.width
            spacing: Theme.AppTheme.spacingMd

            Label {
                Layout.fillWidth: true
                text: {
                    const state = root.selectedTaskState()
                    const taskName = String(state.name || root.taskData.title || "selected task")
                    return "Post a collaboration update for " + taskName + ", mention collaborators with @handle, and queue attachment or shared-document references."
                }
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 540 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label {
                    text: "Insert mention"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    ComboBox {
                        id: mentionCombo
                        Layout.fillWidth: true
                        model: root.mentionOptions || []
                        textRole: "label"
                    }

                    AppControls.PrimaryButton {
                        text: "Insert"
                        enabled: (root.mentionOptions || []).length > 0
                        onClicked: root.insertSelectedMention()
                    }
                }

                Label {
                    text: "Link shared document"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    ComboBox {
                        id: documentCombo
                        Layout.fillWidth: true
                        model: root.documentOptions || []
                        textRole: "label"
                    }

                    AppControls.PrimaryButton {
                        text: "Queue"
                        enabled: (root.documentOptions || []).length > 0
                        onClicked: root.queueSelectedDocument()
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                text: "Comment"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            TextArea {
                id: commentArea
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                placeholderText: "Add an update, handoff note, or question for the task team."
                wrapMode: TextEdit.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.PrimaryButton {
                    text: "Attach File"
                    onClicked: attachmentDialog.open()
                }

                Item { Layout.fillWidth: true }
            }

            Label {
                Layout.fillWidth: true
                text: root.pendingAttachments.length > 0
                    ? "Attachments: " + root.pendingAttachments.join(", ")
                    : "Attachments: none"
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: root.pendingDocuments.length > 0
                    ? "Linked documents: " + root.pendingDocuments.map(function(item) { return String(item.label || "") }).join(", ")
                    : "Linked documents: none"
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item { Layout.fillWidth: true }

        Button {
            text: "Cancel"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            text: "Post Update"
            enabled: String(root.selectedTaskState().taskId || root.selectedTaskState().id || "").length > 0
                && String(commentArea.text || "").trim().length > 0
            onClicked: root.submitted(root.buildPayload())
        }
    }
}
