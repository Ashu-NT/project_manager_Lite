pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Dialogs
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import support.sections 1.0 as SupportSections

ColumnLayout {
    id: root
    spacing: 0

    // -- Settings' own overview (System Information group) ------------
    property PlatformControllers.PlatformSettingsWorkspaceController workspaceController: null
    property bool busy: false

    // -- Support content (Runtime & Operations / Support & Troubleshooting)
    property PlatformControllers.PlatformSupportWorkspaceController supportController: null

    property var supportSettings: root.supportController ? root.supportController.supportSettings : ({})
    property var supportPaths:    root.supportController ? root.supportController.supportPaths    : ({})
    property var updateStatus:    root.supportController ? root.supportController.updateStatus    : ({})
    property var activityFeed:    root.supportController ? root.supportController.activityFeed    : ({ items: [], emptyState: "No support activity" })
    property var bundleState:     root.supportController ? root.supportController.bundleState     : ({})

    readonly property bool _supportBusy: root.supportController ? root.supportController.isBusy : false
    property var _pendingInstallPayload: null

    FileDialog {
        id: diagnosticsSaveDialog
        title: "Save Diagnostics Bundle"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Zip archive (*.zip)"]
        currentFile: {
            const now = new Date()
            const stamp = String(now.getFullYear()) + String(now.getMonth() + 1).padStart(2, "0") + String(now.getDate()).padStart(2, "0")
                + "_" + String(now.getHours()).padStart(2, "0") + String(now.getMinutes()).padStart(2, "0") + String(now.getSeconds()).padStart(2, "0")
            const base = String(root.supportPaths.dataDirectoryUrl || "")
            return base.length > 0 ? base + "/pm_diagnostics_" + stamp + ".zip" : ""
        }
        onAccepted: { if (root.supportController) root.supportController.exportDiagnosticsTo(String(selectedFile || "")) }
    }

    AppWidgets.EntityDialog {
        id: installDialog
        title: "Install Update"
        subtitle: "The app will download the installer, prepare the Windows update handoff, then close and relaunch automatically. Continue?"
        primaryText: "Install Now"; primaryIcon: "approve"
        primaryEnabled: !root._supportBusy
        onAccepted: {
            installDialog.close()
            if (root.supportController && root._pendingInstallPayload)
                root.supportController.installAvailableUpdate(root._pendingInstallPayload)
        }
        onRejected: installDialog.close()
    }

    Flickable {
        Layout.fillWidth: true
        Layout.fillHeight: true
        contentWidth: width
        contentHeight: _content.implicitHeight + Theme.AppTheme.marginLg * 2
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        ColumnLayout {
            id: _content
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.AppTheme.marginLg
            spacing: Theme.AppTheme.spacingLg

            // -- System Information -----------------------------------
            AppWidgets.SectionHeading { Layout.fillWidth: true; label: "System Information" }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                Repeater {
                    model: root.workspaceController
                        ? (root.workspaceController.overview.sections || []) : []

                    delegate: AppWidgets.OverviewSectionCard {
                        required property var modelData
                        title: modelData.title || ""
                        emptyState: modelData.emptyState || ""
                    }
                }
            }

            // -- Runtime & Operations ----------------------------------
            AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Runtime & Operations" }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 240
                spacing: 0

                SupportSections.AdminSupportReleasePanel {
                    id: releasePanel
                    supportSettings: root.supportSettings
                    updateStatus: root.updateStatus
                    isBusy: root._supportBusy

                    onSaveSettingsRequested: function(ch, auto, manifest) { if (root.supportController) root.supportController.saveSettings({ "updateChannel": ch, "updateAutoCheck": auto, "updateManifestSource": manifest }) }
                    onCheckUpdatesRequested: function(ch, auto, manifest) { if (root.supportController) root.supportController.checkForUpdates({ "updateChannel": ch, "updateAutoCheck": auto, "updateManifestSource": manifest }) }
                    onInstallUpdateRequested: function(ch, auto, manifest) { root._pendingInstallPayload = { "updateChannel": ch, "updateAutoCheck": auto, "updateManifestSource": manifest }; installDialog.open() }
                    onOpenDownloadRequested: { if (root.supportController) root.supportController.openUpdateDownload() }
                }

                Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 1; color: Theme.AppTheme.divider }

                SupportSections.AdminSupportRuntimePanel {
                    supportSettings: root.supportSettings
                    updateStatus: root.updateStatus
                }
            }

            SupportSections.AdminSupportPathsPanel {
                Layout.fillWidth: true
                supportSettings: root.supportSettings
                supportPaths: root.supportPaths
                bundleState: root.bundleState
                onOpenLogsRequested: { if (root.supportController) root.supportController.openLogsFolder() }
                onOpenDataRequested: { if (root.supportController) root.supportController.openDataFolder() }
            }

            // -- Support & Troubleshooting -----------------------------
            AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Support & Troubleshooting" }

            SupportSections.AdminSupportDiagnosticsPanel {
                id: diagnosticsPanel
                Layout.fillWidth: true
                bundleState: root.bundleState
                isBusy: root._supportBusy
                incidentId: root.supportController ? root.supportController.incidentId : ""

                onExportDiagnosticsRequested: diagnosticsSaveDialog.open()
                onReportIncidentRequested: { if (root.supportController) root.supportController.reportIncident() }
                onNewIncidentIdRequested: { if (root.supportController) root.supportController.newIncidentId() }
                onCopyIncidentIdRequested: { if (root.supportController) root.supportController.copyIncidentId() }
                onSetIncidentIdRequested: function(id) { if (root.supportController) root.supportController.setIncidentId(id) }
                onOpenLatestDiagnosticsRequested: { if (root.supportController) root.supportController.openLatestDiagnostics() }
                onOpenLatestIncidentReportRequested: { if (root.supportController) root.supportController.openLatestIncidentReport() }
            }

            SupportSections.AdminSupportActivityPanel {
                Layout.fillWidth: true
                activityFeed: root.activityFeed
            }
        }
    }
}
