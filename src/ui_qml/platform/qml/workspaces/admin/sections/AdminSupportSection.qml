pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import "../components"

ColumnLayout {
    id: root
    spacing: 0

    // ── Public API ────────────────────────────────────────────────
    property PlatformControllers.PlatformSupportWorkspaceController supportController

    property var supportSettings: root.supportController ? root.supportController.supportSettings : ({})
    property var supportPaths:    root.supportController ? root.supportController.supportPaths    : ({})
    property var updateStatus:    root.supportController ? root.supportController.updateStatus    : ({})
    property var activityFeed:    root.supportController ? root.supportController.activityFeed    : ({ items: [], emptyState: "No support activity" })
    property var bundleState:     root.supportController ? root.supportController.bundleState     : ({})

    readonly property bool _busy: root.supportController ? root.supportController.isBusy : false
    property string _searchText: ""

    // ── Lifecycle ─────────────────────────────────────────────────
    Connections {
        target: root.supportController
        function onSupportSettingsChanged() { releasePanel.syncFromController() }
        function onIncidentIdChanged() {
            diagnosticsPanel.incidentId = root.supportController ? root.supportController.incidentId : ""
        }
    }

    // ── Export dialog ─────────────────────────────────────────────
    FileDialog {
        id: diagnosticsSaveDialog
        title:       "Save Diagnostics Bundle"
        fileMode:    FileDialog.SaveFile
        nameFilters: ["Zip archive (*.zip)"]
        currentFile: {
            const now   = new Date()
            const stamp = String(now.getFullYear()) + String(now.getMonth() + 1).padStart(2, "0") + String(now.getDate()).padStart(2, "0")
                + "_" + String(now.getHours()).padStart(2, "0") + String(now.getMinutes()).padStart(2, "0") + String(now.getSeconds()).padStart(2, "0")
            const base  = String(root.supportPaths.dataDirectoryUrl || "")
            return base.length > 0 ? base + "/pm_diagnostics_" + stamp + ".zip" : ""
        }
        onAccepted: { if (root.supportController) root.supportController.exportDiagnosticsTo(String(selectedFile || "")) }
    }

    AppWidgets.EntityDialog {
        id: installDialog
        title: "Install Update"
        subtitle: "The app will download the installer, prepare the Windows update handoff, then close and relaunch automatically. Continue?"
        primaryText: "Install Now"; primaryIcon: "approve"
        primaryEnabled: !root._busy; width: 460
        onAccepted: {
            installDialog.close()
            if (root.supportController && root._pendingInstallPayload)
                root.supportController.installAvailableUpdate(root._pendingInstallPayload)
        }
        onRejected: installDialog.close()
    }
    property var _pendingInstallPayload: null

    // ── Section title bar ─────────────────────────────────────────
    Rectangle {
        Layout.fillWidth: true; Layout.preferredHeight: Theme.AppTheme.toolbarHeight - 6
        color: Theme.AppTheme.surfaceRaised; z: 1

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.AppTheme.divider
        }
        AppControls.Label {
            anchors.left: parent.left; anchors.leftMargin: Theme.AppTheme.marginMd; anchors.verticalCenter: parent.verticalCenter
            text: "Support"; color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true
        }
    }

    // ── Toolbar + state banners ───────────────────────────────────
    AppWidgets.TableToolbar {
        id: supportToolbar
        Layout.fillWidth:  true
        searchPlaceholder: "Search diagnostics..."
        showFilter: true; showViews: true; showRefresh: true
        isBusy: root._busy
        onSearchChanged:    function(text) { root._searchText = text }
        onFilterClicked:    supportFilterPopup.open()
        onViewsClicked:     supportViewsPopup.open()
        onRefreshRequested: { if (root.supportController) root.supportController.refresh() }
    }

    AppWidgets.InlineMessage { Layout.fillWidth: true; visible: root._busy && String(root.supportController ? root.supportController.errorMessage : "").length === 0; tone: "info"; message: "Processing..." }
    AppWidgets.InlineMessage { Layout.fillWidth: true; visible: String(root.supportController ? root.supportController.errorMessage : "").length > 0; tone: "danger"; message: root.supportController ? root.supportController.errorMessage : "" }
    AppWidgets.InlineMessage { Layout.fillWidth: true; visible: String(root.supportController ? root.supportController.feedbackMessage : "").length > 0 && String(root.supportController ? root.supportController.errorMessage : "").length === 0; tone: "success"; message: root.supportController ? root.supportController.feedbackMessage : "" }

    // ── Release Management + Runtime Status ───────────────────────
    RowLayout {
        Layout.fillWidth: true; Layout.preferredHeight: 240; spacing: 0

        AdminSupportReleasePanel {
            id: releasePanel
            supportSettings: root.supportSettings
            updateStatus:    root.updateStatus
            isBusy:          root._busy

            function syncFromController() {
                const ch = String(root.supportSettings.updateChannel || "stable")
                for (let i = 0; i < model.count; i++) {
                    if (String((model.get(i) || {}).value || "") === ch) { currentIndex = i; break }
                }
            }

            onSaveSettingsRequested:    function(ch, auto, manifest) { if (root.supportController) root.supportController.saveSettings({ "updateChannel": ch, "updateAutoCheck": auto, "updateManifestSource": manifest }) }
            onCheckUpdatesRequested:    function(ch, auto, manifest) { if (root.supportController) root.supportController.checkForUpdates({ "updateChannel": ch, "updateAutoCheck": auto, "updateManifestSource": manifest }) }
            onInstallUpdateRequested:   function(ch, auto, manifest) { root._pendingInstallPayload = { "updateChannel": ch, "updateAutoCheck": auto, "updateManifestSource": manifest }; installDialog.open() }
            onOpenDownloadRequested:    { if (root.supportController) root.supportController.openUpdateDownload() }
        }

        Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 1; color: Theme.AppTheme.divider }

        AdminSupportRuntimePanel {
            supportSettings: root.supportSettings
            updateStatus:    root.updateStatus
        }
    }

    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }

    // ── Incident Diagnostics ──────────────────────────────────────
    AdminSupportDiagnosticsPanel {
        id: diagnosticsPanel
        Layout.fillWidth:  true
        bundleState:       root.bundleState
        isBusy:            root._busy
        incidentId:        root.supportController ? root.supportController.incidentId : ""

        onExportDiagnosticsRequested:        diagnosticsSaveDialog.open()
        onReportIncidentRequested:           { if (root.supportController) root.supportController.reportIncident() }
        onNewIncidentIdRequested:            { if (root.supportController) root.supportController.newIncidentId() }
        onCopyIncidentIdRequested:           { if (root.supportController) root.supportController.copyIncidentId() }
        onSetIncidentIdRequested:            function(id) { if (root.supportController) root.supportController.setIncidentId(id) }
        onOpenLatestDiagnosticsRequested:    { if (root.supportController) root.supportController.openLatestDiagnostics() }
        onOpenLatestIncidentReportRequested: { if (root.supportController) root.supportController.openLatestIncidentReport() }
    }

    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }

    // ── Runtime Paths ─────────────────────────────────────────────
    AdminSupportPathsPanel {
        Layout.fillWidth: true
        supportSettings:  root.supportSettings
        supportPaths:     root.supportPaths
        bundleState:      root.bundleState
        onOpenLogsRequested: { if (root.supportController) root.supportController.openLogsFolder() }
        onOpenDataRequested: { if (root.supportController) root.supportController.openDataFolder() }
    }

    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }

    // ── Support Activity ──────────────────────────────────────────
    AdminSupportActivityPanel {
        Layout.fillWidth: true
        activityFeed: root.activityFeed
    }

    // ── Filter popup ──────────────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: supportFilterPopup
        anchorItem: supportToolbar.filterButtonItem; implicitWidth: 280; padding: Theme.AppTheme.marginMd
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: Theme.AppTheme.surfaceRaised; radius: Theme.AppTheme.radiusMd; border.color: Theme.AppTheme.divider; border.width: 1 }

        ColumnLayout {
            width: parent.width; spacing: Theme.AppTheme.spacingMd
            AppControls.Label { text: "Filter Support"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.bodySize; font.bold: true }
            AppControls.Label { Layout.fillWidth: true; text: "Activity type and date filters will appear here."; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; wrapMode: Text.WordWrap }
            AppControls.SecondaryButton { Layout.alignment: Qt.AlignRight; text: "Close"; onClicked: supportFilterPopup.close() }
        }
    }

    // ── Views popup ───────────────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: supportViewsPopup
        anchorItem: supportToolbar.viewsButtonItem; implicitWidth: 220; padding: 4
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: Theme.AppTheme.surfaceRaised; radius: Theme.AppTheme.radiusMd; border.color: Theme.AppTheme.divider; border.width: 1 }

        Column {
            width: parent.width; spacing: 2
            Repeater {
                model: ["All Activity", "Updates", "Diagnostics", "Incidents", "Warnings"]
                delegate: Rectangle {
                    required property string modelData
                    width: parent.width; height: 34; radius: Theme.AppTheme.radiusMd
                    color: _svMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"
                    AppControls.Label {
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                    }
                    MouseArea { id: _svMA; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: supportViewsPopup.close() }
                }
            }
        }
    }
}
