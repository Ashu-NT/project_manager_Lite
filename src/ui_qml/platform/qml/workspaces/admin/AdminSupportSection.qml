import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets

GridLayout {
    id: root

    property PlatformControllers.PlatformSupportWorkspaceController supportController
    property var supportSettings: root.supportController ? root.supportController.supportSettings : ({})
    property var supportPaths: root.supportController ? root.supportController.supportPaths : ({})
    property var updateStatus: root.supportController ? root.supportController.updateStatus : ({})
    property var activityFeed: root.supportController ? root.supportController.activityFeed : ({
        "title": "Support Activity",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property var bundleState: root.supportController ? root.supportController.bundleState : ({})

    columns: width > 1320 ? 2 : 1
    columnSpacing: Theme.AppTheme.spacingMd
    rowSpacing: Theme.AppTheme.spacingMd

    function syncFormFromController() {
        const channel = String(root.supportSettings.updateChannel || "stable")
        let matchIndex = -1
        for (let index = 0; index < channelCombo.count; index += 1) {
            const option = channelCombo.model[index]
            if (String(option.value || "") === channel) {
                matchIndex = index
                break
            }
        }
        channelCombo.currentIndex = matchIndex >= 0 ? matchIndex : 0
        autoCheckBox.checked = Boolean(root.supportSettings.updateAutoCheck)
        manifestField.text = String(root.supportSettings.updateManifestSource || "")
        incidentField.text = root.supportController ? root.supportController.incidentId : ""
    }

    function settingsPayload() {
        const selectedChannel = channelCombo.currentIndex >= 0 && channelCombo.currentIndex < channelCombo.count
            ? String((channelCombo.model[channelCombo.currentIndex] || {}).value || "stable")
            : "stable"
        return {
            "updateChannel": selectedChannel,
            "updateAutoCheck": autoCheckBox.checked,
            "updateManifestSource": manifestField.text.trim()
        }
    }

    Component.onCompleted: syncFormFromController()

    Connections {
        target: root.supportController

        function onSupportSettingsChanged() {
            root.syncFormFromController()
        }

        function onIncidentIdChanged() {
            incidentField.text = root.supportController ? root.supportController.incidentId : ""
        }
    }

    Rectangle {
        Layout.fillWidth: true
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
        implicitHeight: updateColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

        ColumnLayout {
            id: updateColumn

            anchors.fill: parent
            anchors.margins: Theme.AppTheme.marginLg
            spacing: Theme.AppTheme.spacingMd

            Label {
                Layout.fillWidth: true
                text: "Support Updates"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.titleSize
                font.bold: true
            }

            Label {
                Layout.fillWidth: true
                text: "Persist the platform update channel, check release manifests, and surface runtime support metadata through the desktop API."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                ComboBox {
                    id: channelCombo

                    Layout.preferredWidth: 180
                    model: root.supportSettings.channelOptions || []
                    textRole: "label"
                }

                CheckBox {
                    id: autoCheckBox

                    text: "Auto-check at startup"
                }
            }

            TextField {
                id: manifestField

                Layout.fillWidth: true
                placeholderText: "Update manifest source"
            }

            GridLayout {
                Layout.fillWidth: true
                columns: width > 520 ? 3 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: "App Version: " + String(root.supportSettings.appVersion || "-")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: "Theme: " + String(root.supportSettings.themeMode || "-")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: "Governance: " + String(root.supportSettings.governanceMode || "-")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                border.color: Theme.AppTheme.border
                implicitHeight: statusColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)

                ColumnLayout {
                    id: statusColumn

                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        Label {
                            Layout.fillWidth: true
                            text: "Release Status"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                        }

                        Rectangle {
                            radius: Theme.AppTheme.radiusMd
                            color: Theme.AppTheme.accentSoft
                            border.color: Theme.AppTheme.accent
                            implicitHeight: statusLabel.implicitHeight + Theme.AppTheme.marginSm * 2
                            implicitWidth: statusLabel.implicitWidth + Theme.AppTheme.marginMd * 2

                            Label {
                                id: statusLabel

                                anchors.centerIn: parent
                                text: String(root.updateStatus.statusLabel || "Ready")
                                color: Theme.AppTheme.accent
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: String(root.updateStatus.summary || "")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "Current: " + String(root.updateStatus.currentVersion || "-")
                            + " | Latest: " + String(root.updateStatus.latestVersion || "-")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: String(root.updateStatus.notes || "").length > 0
                        text: "Notes: " + String(root.updateStatus.notes || "")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: String(root.updateStatus.sha256 || "").length > 0
                        text: "SHA256: " + String(root.updateStatus.sha256 || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WrapAnywhere
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.PrimaryButton {
                    text: "Save Settings"
                    enabled: root.supportController ? !root.supportController.isBusy : false
                    onClicked: root.supportController.saveSettings(root.settingsPayload())
                }

                AppControls.PrimaryButton {
                    text: "Check Updates"
                    enabled: root.supportController ? !root.supportController.isBusy : false
                    onClicked: root.supportController.checkForUpdates(root.settingsPayload())
                }

                AppControls.PrimaryButton {
                    text: "Open Download"
                    enabled: root.supportController
                        ? (!root.supportController.isBusy && Boolean(root.updateStatus.canOpenDownload))
                        : false
                    onClicked: root.supportController.openUpdateDownload()
                }

                Item {
                    Layout.fillWidth: true
                }
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
        implicitHeight: incidentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

        ColumnLayout {
            id: incidentColumn

            anchors.fill: parent
            anchors.margins: Theme.AppTheme.marginLg
            spacing: Theme.AppTheme.spacingMd

            Label {
                Layout.fillWidth: true
                text: "Incident And Diagnostics"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.titleSize
                font.bold: true
            }

            Label {
                Layout.fillWidth: true
                text: "Package diagnostics, prepare incident bundles, and open runtime support folders without dropping back into the old widget support tab."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            TextField {
                id: incidentField

                Layout.fillWidth: true
                placeholderText: "Incident trace ID"
                onEditingFinished: {
                    if (root.supportController !== null) {
                        root.supportController.setIncidentId(text.trim())
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.PrimaryButton {
                    text: "New Trace"
                    enabled: root.supportController ? !root.supportController.isBusy : false
                    onClicked: root.supportController.newIncidentId()
                }

                AppControls.PrimaryButton {
                    text: "Copy Trace"
                    enabled: root.supportController ? !root.supportController.isBusy : false
                    onClicked: root.supportController.copyIncidentId()
                }

                Item {
                    Layout.fillWidth: true
                }
            }

            Label {
                Layout.fillWidth: true
                text: "Support Email: " + String(root.supportSettings.supportEmail || root.bundleState.supportEmail || "-")
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "Logs: " + String(root.supportPaths.logsDirectoryPath || "-")
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WrapAnywhere
            }

            Label {
                Layout.fillWidth: true
                text: "Data: " + String(root.supportPaths.dataDirectoryPath || "-")
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WrapAnywhere
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: "Last Diagnostics Bundle"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: String(root.bundleState.lastDiagnosticsPath || "No diagnostics bundle exported yet.")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WrapAnywhere
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: "Last Incident Report"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: String(root.bundleState.lastIncidentReportPath || "No incident report package created yet.")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WrapAnywhere
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.PrimaryButton {
                    text: "Export Diagnostics"
                    enabled: root.supportController ? !root.supportController.isBusy : false
                    onClicked: root.supportController.exportDiagnostics()
                }

                AppControls.PrimaryButton {
                    text: "Report Incident"
                    enabled: root.supportController ? !root.supportController.isBusy : false
                    onClicked: root.supportController.reportIncident()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.PrimaryButton {
                    text: "Open Logs"
                    enabled: root.supportController ? !root.supportController.isBusy : false
                    onClicked: root.supportController.openLogsFolder()
                }

                AppControls.PrimaryButton {
                    text: "Open Data"
                    enabled: root.supportController ? !root.supportController.isBusy : false
                    onClicked: root.supportController.openDataFolder()
                }

                AppControls.PrimaryButton {
                    text: "Open Diagnostics"
                    enabled: root.supportController
                        ? (!root.supportController.isBusy && String(root.bundleState.lastDiagnosticsUrl || "").length > 0)
                        : false
                    onClicked: root.supportController.openLatestDiagnostics()
                }

                AppControls.PrimaryButton {
                    text: "Open Incident Package"
                    enabled: root.supportController
                        ? (!root.supportController.isBusy && String(root.bundleState.lastIncidentReportUrl || "").length > 0)
                        : false
                    onClicked: root.supportController.openLatestIncidentReport()
                }
            }
        }
    }

    PlatformWidgets.RecordListCard {
        Layout.fillWidth: true
        Layout.columnSpan: root.columns
        title: root.activityFeed.title || "Support Activity"
        subtitle: root.activityFeed.subtitle || ""
        emptyState: root.activityFeed.emptyState || ""
        items: root.activityFeed.items || []
        actionsEnabled: false
    }
}
