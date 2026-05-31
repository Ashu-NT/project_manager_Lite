pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var workspaceController: null

    modal: true
    width: 680
    height: Math.min(720, parent ? parent.height - Theme.AppTheme.marginLg * 2 : 720)
    title: "Import Project Plan"
    closePolicy: Popup.CloseOnEscape
    showPrimary: false
    showSecondary: false

    readonly property var _preview: root.workspaceController
        ? (root.workspaceController.importPreview || {}) : ({})
    readonly property bool _isBusy: root.workspaceController
        ? root.workspaceController.isImportBusy : false
    readonly property string _importError: root.workspaceController
        ? (root.workspaceController.importError || "") : ""
    readonly property bool _hasPreview: String(root._preview.sessionId || "").length > 0

    property string _selectedFormat: "csv"
    property string _selectedFilePath: ""
    property string _selectedFileName: ""

    readonly property var _formatOptions: [
        { "value": "csv",            "label": "CSV (comma-separated)",          "hint": "CSV task list" },
        { "value": "ms_project_xml", "label": "MS Project XML (.xml)",          "hint": "Microsoft Project XML export" },
        { "value": "p6_xer",         "label": "Oracle Primavera P6 XER (.xer)", "hint": "P6 XER table export" }
    ]

    onAboutToHide: {
        if (root.workspaceController) root.workspaceController.cancelImport()
        root._selectedFilePath = ""
        root._selectedFileName = ""
        root._selectedFormat = "csv"
    }

    FileDialog {
        id: filePicker
        title: "Select Import File"
        fileMode: FileDialog.OpenFile
        nameFilters: {
            if (root._selectedFormat === "csv")            return ["CSV files (*.csv)", "All files (*)"]
            if (root._selectedFormat === "ms_project_xml") return ["XML files (*.xml)", "All files (*)"]
            if (root._selectedFormat === "p6_xer")         return ["XER files (*.xer)", "All files (*)"]
            return ["All files (*)"]
        }
        onAccepted: {
            const path = filePicker.selectedFile.toString()
            root._selectedFilePath = path
            const parts = path.replace(/\\/g, "/").split("/")
            root._selectedFileName = parts[parts.length - 1]
        }
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root._isBusy
            tone: "info"
            message: "Processing file..."
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root._importError.length > 0 && !root._isBusy
            tone: "danger"
            message: root._importError
        }

        // ── Step 1: format + file picker ─────────────────────────────
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd
            visible: !root._hasPreview

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Source Format"
                    font.bold: true
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.family: Theme.AppTheme.fontFamily
                    color: Theme.AppTheme.textMuted
                }

                AppControls.ComboBox {
                    Layout.fillWidth: true
                    model: root._formatOptions
                    textRole: "label"
                    enabled: !root._isBusy
                    currentIndex: {
                        for (let i = 0; i < root._formatOptions.length; i++) {
                            if (root._formatOptions[i].value === root._selectedFormat) return i
                        }
                        return 0
                    }
                    onActivated: function(index) {
                        root._selectedFormat = root._formatOptions[index].value
                        root._selectedFilePath = ""
                        root._selectedFileName = ""
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "File"
                    font.bold: true
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.family: Theme.AppTheme.fontFamily
                    color: Theme.AppTheme.textMuted
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.TextField {
                        Layout.fillWidth: true
                        readOnly: true
                        enabled: false
                        placeholderText: "No file selected"
                        text: root._selectedFileName
                    }

                    AppControls.SecondaryButton {
                        text: "Browse..."
                        iconName: "upload"
                        enabled: !root._isBusy
                        onClicked: filePicker.open()
                    }
                }
            }
        }

        // ── Step 2: preview ───────────────────────────────────────────
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.AppTheme.spacingMd
            visible: root._hasPreview

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                Repeater {
                    model: [
                        { "label": "Total",    "value": String(root._preview.totalRows   || 0), "ok": false, "warn": false },
                        { "label": "Valid",    "value": String(root._preview.validRows   || 0), "ok": true,  "warn": false },
                        { "label": "Errors",   "value": String(root._preview.errorRows   || 0), "ok": false, "warn": (root._preview.errorRows || 0) > 0 },
                        { "label": "Warnings", "value": String(root._preview.warningRows || 0), "ok": false, "warn": false }
                    ]

                    delegate: Rectangle {
                        id: delegateRoot

                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: _sc.implicitHeight + Theme.AppTheme.spacingMd
                        radius: Theme.AppTheme.radiusSm
                        color: Theme.AppTheme.surfaceOverlay

                        ColumnLayout {
                            id: _sc
                            anchors.centerIn: parent
                            spacing: 2

                            AppControls.Label {
                                Layout.alignment: Qt.AlignHCenter
                                text: delegateRoot.modelData.value
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.subtitleSize
                                font.family: Theme.AppTheme.fontFamily
                                color: delegateRoot.modelData.warn ? Theme.AppTheme.danger
                                    : (delegateRoot.modelData.ok ? Theme.AppTheme.success : Theme.AppTheme.textPrimary)
                            }

                            AppControls.Label {
                                Layout.alignment: Qt.AlignHCenter
                                text: delegateRoot.modelData.label
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                        }
                    }
                }
            }

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: (root._preview.errorRows || 0) > 0
                tone: "danger"
                message: (root._preview.errorRows || 0) + " row(s) have errors and will be skipped on import."
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                Column {
                    width: parent.width
                    spacing: 1

                    // Header row
                    Rectangle {
                        width: parent.width
                        implicitHeight: _hdr.implicitHeight + Theme.AppTheme.spacingXs
                        color: Theme.AppTheme.surfaceOverlay

                        RowLayout {
                            id: _hdr
                            anchors {
                                left: parent.left; right: parent.right
                                verticalCenter: parent.verticalCenter
                                leftMargin: Theme.AppTheme.marginSm
                                rightMargin: Theme.AppTheme.marginSm
                            }
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: "#"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                                Layout.preferredWidth: 30
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: "Name"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.Label {
                                text: "Start"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                                Layout.preferredWidth: 90
                            }
                            AppControls.Label {
                                text: "Finish"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                                Layout.preferredWidth: 90
                            }
                        }
                    }

                    Repeater {
                        model: root._preview.rows || []

                        delegate: Rectangle {
                            id: _delegateRoot
                            required property var modelData
                            required property int index
                            width: parent ? parent.width : 0
                            implicitHeight: _rl.implicitHeight + Theme.AppTheme.spacingXs
                            color: index % 2 === 0 ? Theme.AppTheme.surface : Theme.AppTheme.surfaceOverlay

                            RowLayout {
                                id: _rl
                                anchors {
                                    left: parent.left; right: parent.right
                                    verticalCenter: parent.verticalCenter
                                    leftMargin: Theme.AppTheme.marginSm
                                    rightMargin: Theme.AppTheme.marginSm
                                }
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.Label {
                                    text: String(_delegateRoot.modelData.rowNumber || "")
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.family: Theme.AppTheme.fontFamily
                                    Layout.preferredWidth: 30
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: _delegateRoot.modelData.name || "(no name)"
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.family: Theme.AppTheme.fontFamily
                                    color: _delegateRoot.modelData.hasErrors ? Theme.AppTheme.danger : Theme.AppTheme.textPrimary
                                    elide: Text.ElideRight
                                }

                                AppControls.Label {
                                    text: _delegateRoot.modelData.startDate || ""
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.family: Theme.AppTheme.fontFamily
                                    Layout.preferredWidth: 90
                                }

                                AppControls.Label {
                                    text: _delegateRoot.modelData.endDate || ""
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.family: Theme.AppTheme.fontFamily
                                    Layout.preferredWidth: 90
                                }
                            }
                        }
                    }
                }
            }
        }

        Item { Layout.fillHeight: true; visible: !root._hasPreview }
    }

    footer: Item {
        implicitHeight: footerRow.implicitHeight + Theme.AppTheme.marginMd * 2
        RowLayout {
            id: footerRow

            anchors {
                left: parent.left
                right: parent.right
                verticalCenter: parent.verticalCenter
                leftMargin: Theme.AppTheme.marginMd
                rightMargin: Theme.AppTheme.marginMd
            }

            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: root._hasPreview ? "Back" : "Cancel"
                iconName: root._hasPreview ? "back" : "close"
                enabled: !root._isBusy
                onClicked: {
                    if (root._hasPreview) {
                        if (root.workspaceController) root.workspaceController.cancelImport()
                    } else {
                        root.close()
                    }
                }
            }

            Item { Layout.fillWidth: true }

            AppControls.PrimaryButton {
                visible: !root._hasPreview
                text: "Preview"
                iconName: "search"
                enabled: !root._isBusy && root._selectedFilePath.length > 0
                onClicked: {
                    if (root.workspaceController) {
                        root.workspaceController.previewImport(root._selectedFilePath, root._selectedFormat)
                    }
                }
            }

            AppControls.PrimaryButton {
                visible: root._hasPreview
                text: "Import"
                iconName: "upload"
                enabled: !root._isBusy && (root._preview.canCommit || false)
                onClicked: {
                    if (root.workspaceController) {
                        const result = root.workspaceController.executeImport(
                            String(root._preview.sessionId || "")
                        )
                        if (result && result.ok) root.close()
                    }
                }
            }
    }   }
}
