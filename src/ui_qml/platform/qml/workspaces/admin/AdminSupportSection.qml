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

    // ── Inline component: compact key-value metadata row ──────────
    component MetaRow: RowLayout {
        id: _mr
        property string rowLabel: ""
        property string rowValue: ""
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingXs

        AppControls.Label {
            text:               _mr.rowLabel
            color:              Theme.AppTheme.textMuted
            font.family:        Theme.AppTheme.fontFamily
            font.pixelSize:     Theme.AppTheme.captionSize
            font.bold:          true
            Layout.preferredWidth: 100
        }
        AppControls.Label {
            Layout.fillWidth: true
            text:           _mr.rowValue || "-"
            color:          Theme.AppTheme.textSecondary
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            elide:          Text.ElideRight
        }
    }

    // ── Inline component: path row with optional open button ──────
    component PathRow: Rectangle {
        id: _pr
        property string rowLabel: ""
        property string rowValue: ""
        property bool   canOpen:  false
        signal openRequested()

        Layout.fillWidth: true
        Layout.preferredHeight: 36
        color:  "transparent"

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }

        RowLayout {
            anchors.fill:        parent
            anchors.leftMargin:  Theme.AppTheme.marginMd
            anchors.rightMargin: Theme.AppTheme.marginSm
            spacing:             Theme.AppTheme.spacingXs

            AppControls.Label {
                text:           _pr.rowLabel
                color:          Theme.AppTheme.textMuted
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold:      true
                Layout.preferredWidth: 160
            }

            AppControls.Label {
                Layout.fillWidth: true
                text:           _pr.rowValue.length > 0 ? _pr.rowValue : "-"
                color:          Theme.AppTheme.textSecondary
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                elide:          Text.ElideMiddle
            }

            Rectangle {
                visible: _pr.canOpen
                Layout.preferredWidth: 22; Layout.preferredHeight: 22; radius: Theme.AppTheme.radiusMd
                color: _openMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                AppIcons.AppIcon {
                    anchors.centerIn: parent
                    name: "view"; size: 10
                    iconColor: Theme.AppTheme.textMuted
                }

                MouseArea {
                    id: _openMA
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape:  Qt.PointingHandCursor
                    onClicked:    _pr.openRequested()
                }
            }
        }
    }

    // ── Helper functions (wiring preserved) ──────────────────────
    function diagnosticsDefaultTarget() {
        const now    = new Date()
        const stamp  = String(now.getFullYear())
            + String(now.getMonth() + 1).padStart(2, "0")
            + String(now.getDate()).padStart(2, "0")
            + "_"
            + String(now.getHours()).padStart(2, "0")
            + String(now.getMinutes()).padStart(2, "0")
            + String(now.getSeconds()).padStart(2, "0")
        const base = String(root.supportPaths.dataDirectoryUrl || "")
        return base.length > 0 ? base + "/pm_diagnostics_" + stamp + ".zip" : ""
    }

    function syncFormFromController() {
        const channel = String(root.supportSettings.updateChannel || "stable")
        let matchIndex = -1
        for (let i = 0; i < channelCombo.count; i++) {
            if (String((channelCombo.model[i] || {}).value || "") === channel) {
                matchIndex = i; break
            }
        }
        channelCombo.currentIndex = matchIndex >= 0 ? matchIndex : 0
        autoCheckBox.checked  = Boolean(root.supportSettings.updateAutoCheck)
        manifestField.text    = String(root.supportSettings.updateManifestSource || "")
        incidentField.text    = root.supportController ? root.supportController.incidentId : ""
    }

    function settingsPayload() {
        const idx = channelCombo.currentIndex
        const ch  = (idx >= 0 && idx < channelCombo.count)
            ? String((channelCombo.model[idx] || {}).value || "stable") : "stable"
        return {
            "updateChannel":        ch,
            "updateAutoCheck":      autoCheckBox.checked,
            "updateManifestSource": manifestField.text.trim()
        }
    }

    Component.onCompleted: syncFormFromController()

    Connections {
        target: root.supportController
        function onSupportSettingsChanged() { root.syncFormFromController() }
        function onIncidentIdChanged() {
            incidentField.text = root.supportController ? root.supportController.incidentId : ""
        }
    }

    // ── Dialogs (wiring preserved) ────────────────────────────────
    FileDialog {
        id: diagnosticsSaveDialog
        title:       "Save Diagnostics Bundle"
        fileMode:    FileDialog.SaveFile
        nameFilters: ["Zip archive (*.zip)"]
        currentFile: root.diagnosticsDefaultTarget()
        onAccepted: {
            if (root.supportController)
                root.supportController.exportDiagnosticsTo(String(selectedFile || ""))
        }
    }

    AppWidgets.EntityDialog {
        id: installDialog
        title:          "Install Update"
        subtitle:       "The app will download the installer, prepare the Windows update handoff, then close and relaunch automatically. Continue?"
        primaryText:    "Install Now"
        primaryIcon:    "approve"
        primaryEnabled: !root._busy
        width: 460

        onAccepted: {
            installDialog.close()
            if (root.supportController)
                root.supportController.installAvailableUpdate(root.settingsPayload())
        }
        onRejected: installDialog.close()
    }

    // ── Section title bar ─────────────────────────────────────────
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: Theme.AppTheme.toolbarHeight - 6
        color:  Theme.AppTheme.surfaceRaised
        z:      1

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }

        AppControls.Label {
            anchors.left:           parent.left
            anchors.leftMargin:     Theme.AppTheme.marginMd
            anchors.verticalCenter: parent.verticalCenter
            text:           "Support"
            color:          Theme.AppTheme.textPrimary
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold:      true
        }
    }

    // ── TableToolbar ──────────────────────────────────────────────
    AppWidgets.TableToolbar {
        id: supportToolbar
        Layout.fillWidth:  true
        searchPlaceholder: "Search diagnostics..."
        showFilter:        true
        showViews:         true
        showRefresh:       true
        isBusy:            root._busy
        onSearchChanged:    function(text) { root._searchText = text }
        onFilterClicked:    supportFilterPopup.open()
        onViewsClicked:     supportViewsPopup.open()
        onRefreshRequested: { if (root.supportController) root.supportController.refresh() }
    }

    // ── Inline state banner ───────────────────────────────────────
    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root._busy
        tone:    "info"
        message: "Processing..."
    }

    // ── Top panels: Release Management | Runtime Status ───────────
    RowLayout {
        Layout.fillWidth:       true
        Layout.preferredHeight: 240
        spacing: 0

        // ── Release Management ────────────────────────────────────
        ColumnLayout {
            Layout.fillWidth:  true
            Layout.fillHeight: true
            spacing: 0

            AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Release Management" }

            ColumnLayout {
                Layout.fillWidth:    true
                Layout.fillHeight:   true
                Layout.leftMargin:   Theme.AppTheme.marginMd
                Layout.rightMargin:  Theme.AppTheme.marginMd
                Layout.topMargin:    Theme.AppTheme.spacingSm
                Layout.bottomMargin: Theme.AppTheme.spacingSm
                spacing:             Theme.AppTheme.spacingSm

                // Channel + Auto-check
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3

                        AppControls.Label {
                            text:           "Channel"
                            color:          Theme.AppTheme.textMuted
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold:      true
                        }

                        AppControls.ComboBox {
                            id: channelCombo
                            Layout.fillWidth: true
                            enabled:  !root._busy
                            model:    root.supportSettings.channelOptions || []
                            textRole: "label"
                        }
                    }

                    AppControls.CheckBox {
                        id: autoCheckBox
                        Layout.alignment: Qt.AlignBottom
                        text:    "Auto-check at startup"
                        enabled: !root._busy
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                    }
                }

                // Manifest source
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    AppControls.Label {
                        text:           "Manifest Source"
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold:      true
                    }

                    AppControls.TextField {
                        id: manifestField
                        Layout.fillWidth: true
                        enabled:         !root._busy
                        placeholderText: "Update manifest URL or path"
                    }
                }

                Item { Layout.fillHeight: true }

                // Actions
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.PrimaryButton {
                        text: "Save Settings"; iconName: "save"
                        enabled: !root._busy
                        onClicked: { if (root.supportController) root.supportController.saveSettings(root.settingsPayload()) }
                    }

                    AppControls.SecondaryButton {
                        text: "Check Updates"; iconName: "refresh"
                        enabled: !root._busy
                        onClicked: { if (root.supportController) root.supportController.checkForUpdates(root.settingsPayload()) }
                    }

                    AppControls.SecondaryButton {
                        visible: Qt.platform.os === "windows"
                        text:    "Install Now"; iconName: "approve"
                        enabled: !root._busy
                            && Boolean(root.updateStatus.updateAvailable)
                            && Boolean(root.updateStatus.canOpenDownload)
                        onClicked: installDialog.open()
                    }

                    AppControls.SecondaryButton {
                        text:    "Open Download"; iconName: "view"
                        enabled: !root._busy && Boolean(root.updateStatus.canOpenDownload)
                        onClicked: { if (root.supportController) root.supportController.openUpdateDownload() }
                    }

                    Item { Layout.fillWidth: true }
                }
            }
        }

        // Panel divider
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 1; color: Theme.AppTheme.divider
        }

        // ── Runtime Status ────────────────────────────────────────
        ColumnLayout {
            Layout.preferredWidth: 260
            Layout.fillHeight:     true
            spacing: 0

            AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Runtime Status" }

            ColumnLayout {
                Layout.fillWidth:    true
                Layout.fillHeight:   true
                Layout.leftMargin:   Theme.AppTheme.marginMd
                Layout.rightMargin:  Theme.AppTheme.marginMd
                Layout.topMargin:    Theme.AppTheme.spacingSm
                Layout.bottomMargin: Theme.AppTheme.spacingSm
                spacing:             Theme.AppTheme.spacingXs

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingXs

                    AppControls.Label {
                        Layout.fillWidth: true
                        text:           "Release Status"
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold:      true
                    }

                    AppWidgets.StatusChip {
                        status: String(root.updateStatus.statusLabel || "Ready")
                    }
                }

                MetaRow { rowLabel: "App Version"; rowValue: String(root.supportSettings.appVersion    || "-") }
                MetaRow { rowLabel: "Current";     rowValue: String(root.updateStatus.currentVersion   || "-") }
                MetaRow { rowLabel: "Latest";      rowValue: String(root.updateStatus.latestVersion    || "-") }
                MetaRow { rowLabel: "Theme";       rowValue: String(root.supportSettings.themeMode     || "-") }
                MetaRow { rowLabel: "Governance";  rowValue: String(root.supportSettings.governanceMode || "-") }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible:        String(root.updateStatus.notes || "").length > 0
                    text:           String(root.updateStatus.notes || "")
                    color:          Theme.AppTheme.textMuted
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    wrapMode:       Text.WordWrap
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible:        String(root.updateStatus.summary || "").length > 0
                    text:           String(root.updateStatus.summary || "")
                    color:          Theme.AppTheme.textSecondary
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    wrapMode:       Text.WordWrap
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible:        String(root.updateStatus.sha256 || "").length > 0
                    text:           "SHA256: " + String(root.updateStatus.sha256 || "")
                    color:          Theme.AppTheme.textMuted
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    wrapMode:       Text.WrapAnywhere
                    maximumLineCount: 2
                    elide:          Text.ElideRight
                }

                Item { Layout.fillHeight: true }
            }
        }
    }

    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }

    // ── Incident Diagnostics ──────────────────────────────────────
    AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Incident Diagnostics" }

    // Active trace panel
    Rectangle {
        Layout.fillWidth: true
        implicitHeight:   _tracePanel.implicitHeight + Theme.AppTheme.spacingSm * 2
        color:            Theme.AppTheme.surfaceOverlay

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }

        ColumnLayout {
            id: _tracePanel
            anchors {
                left: parent.left; right: parent.right; top: parent.top
                leftMargin: Theme.AppTheme.marginMd; rightMargin: Theme.AppTheme.marginMd
                topMargin:  Theme.AppTheme.spacingSm
            }
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label {
                text:               "ACTIVE TRACE"
                color:              Theme.AppTheme.textMuted
                font.family:        Theme.AppTheme.fontFamily
                font.pixelSize:     Theme.AppTheme.captionSize
                font.bold:          true
                font.letterSpacing: 0.8
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.TextField {
                    id: incidentField
                    Layout.fillWidth: true
                    enabled:         !root._busy
                    placeholderText: "Incident trace ID"
                    onEditingFinished: {
                        if (root.supportController)
                            root.supportController.setIncidentId(text.trim())
                    }
                }

                AppControls.SecondaryButton {
                    text: "New Trace"; iconName: "add"
                    enabled: !root._busy
                    onClicked: { if (root.supportController) root.supportController.newIncidentId() }
                }

                AppControls.SecondaryButton {
                    text: "Copy"; iconName: "export"
                    enabled: !root._busy
                    onClicked: { if (root.supportController) root.supportController.copyIncidentId() }
                }
            }
        }
    }

    // Bundle state rows
    PathRow {
        rowLabel: "Last Diagnostics"
        rowValue: String(root.bundleState.lastDiagnosticsPath || "")
        canOpen:  String(root.bundleState.lastDiagnosticsUrl || "").length > 0
        onOpenRequested: { if (root.supportController) root.supportController.openLatestDiagnostics() }
    }

    PathRow {
        rowLabel: "Last Incident Report"
        rowValue: String(root.bundleState.lastIncidentReportPath || "")
        canOpen:  String(root.bundleState.lastIncidentReportUrl || "").length > 0
        onOpenRequested: { if (root.supportController) root.supportController.openLatestIncidentReport() }
    }

    // Diagnostics action bar
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: Theme.AppTheme.toolbarHeight
        color:  Theme.AppTheme.surfaceOverlay

        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }
        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }

        RowLayout {
            anchors.fill:        parent
            anchors.leftMargin:  Theme.AppTheme.marginMd
            anchors.rightMargin: Theme.AppTheme.marginMd
            spacing:             Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                text: "Export Diagnostics"; iconName: "export"
                enabled: !root._busy
                onClicked: diagnosticsSaveDialog.open()
            }

            AppControls.PrimaryButton {
                text: "Report Incident"; iconName: "approve"
                enabled: !root._busy
                onClicked: { if (root.supportController) root.supportController.reportIncident() }
            }

            Item { Layout.fillWidth: true }
        }
    }

    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }

    // ── Runtime Paths ─────────────────────────────────────────────
    AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Runtime Paths" }

    PathRow {
        rowLabel: "Support Contact"
        rowValue: String(root.supportSettings.supportEmail || root.bundleState.supportEmail || "")
        canOpen:  false
    }

    PathRow {
        rowLabel: "Logs"
        rowValue: String(root.supportPaths.logsDirectoryPath || "")
        canOpen:  true
        onOpenRequested: { if (root.supportController) root.supportController.openLogsFolder() }
    }

    PathRow {
        rowLabel: "Data"
        rowValue: String(root.supportPaths.dataDirectoryPath || "")
        canOpen:  true
        onOpenRequested: { if (root.supportController) root.supportController.openDataFolder() }
    }

    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }

    // ── Support Activity ──────────────────────────────────────────
    AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Support Activity" }

    Item {
        Layout.fillWidth:       true
        Layout.preferredHeight: 220

        ListView {
            id: _activityList
            anchors.fill:      parent
            anchors.topMargin: 4
            clip:              true
            boundsBehavior:    Flickable.StopAtBounds
            spacing:           0
            model:             root.activityFeed.items || []

            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Item {
                id: _actRow
                required property var modelData
                required property int index

                width: ListView.view ? ListView.view.width : 0
                height: 44

                // Timeline dot
                Rectangle {
                    id: _actDot
                    anchors.left:           parent.left
                    anchors.leftMargin:     Theme.AppTheme.marginMd
                    anchors.verticalCenter: parent.verticalCenter
                    width: 7; height: 7; radius: 4
                    color: {
                        const s = (_actRow.modelData.statusLabel || "").toLowerCase()
                        if (s.includes("export") || s.includes("success") || s.includes("approv") || s.includes("install")) return Theme.AppTheme.success
                        if (s.includes("error")  || s.includes("fail")    || s.includes("reject"))                          return Theme.AppTheme.danger
                        if (s.includes("warn"))                                                                              return Theme.AppTheme.warning
                        return Theme.AppTheme.textMuted
                    }
                }

                // Vertical connector
                Rectangle {
                    visible:                  _actRow.index < (ListView.view ? ListView.view.count - 1 : 0)
                    anchors.horizontalCenter: _actDot.horizontalCenter
                    anchors.top:              _actDot.bottom
                    anchors.topMargin:        2
                    anchors.bottom:           parent.bottom
                    width: 1; color: Theme.AppTheme.divider
                }

                ColumnLayout {
                    anchors {
                        left:           _actDot.right
                        leftMargin:     Theme.AppTheme.spacingSm
                        right:          parent.right
                        rightMargin:    Theme.AppTheme.marginSm
                        verticalCenter: parent.verticalCenter
                    }
                    spacing: 2

                    RowLayout {
                        Layout.fillWidth: true
                        spacing:          Theme.AppTheme.spacingXs

                        AppControls.Label {
                            Layout.fillWidth: true
                            text:           _actRow.modelData.title || ""
                            color:          Theme.AppTheme.textPrimary
                            font.family:    Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            elide:          Text.ElideRight
                        }

                        AppWidgets.StatusChip {
                            visible: (_actRow.modelData.statusLabel || "").length > 0
                            status:  _actRow.modelData.statusLabel || ""
                        }
                    }

                    AppControls.Label {
                        visible:        (_actRow.modelData.metaText || "").length > 0
                        text:           _actRow.modelData.metaText || ""
                        color:          Theme.AppTheme.textMuted
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        elide:          Text.ElideRight
                    }
                }
            }
        }

        AppWidgets.EmptyState {
            anchors.centerIn: parent
            width:   Math.min(_activityList.width, 240)
            visible: _activityList.count === 0
            title:   String(root.activityFeed.emptyState || "No support activity recorded")
        }
    }

    // ── Filter popup ──────────────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: supportFilterPopup
        anchorItem: supportToolbar.filterButtonItem
        implicitWidth:       280
        padding:     Theme.AppTheme.marginMd
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color:        Theme.AppTheme.surfaceRaised
            radius:       Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.divider
            border.width: 1
        }

        ColumnLayout {
            width:   parent.width
            spacing: Theme.AppTheme.spacingMd

            AppControls.Label {
                text:           "Filter Support"
                color:          Theme.AppTheme.textPrimary
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold:      true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text:    "Activity type and date filters will appear here."
                color:   Theme.AppTheme.textMuted
                font.family:    Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            AppControls.SecondaryButton {
                Layout.alignment: Qt.AlignRight
                text:     "Close"
                onClicked: supportFilterPopup.close()
            }
        }
    }

    // ── Views popup ───────────────────────────────────────────────
    AppWidgets.AnchoredPopup {
        id: supportViewsPopup
        anchorItem: supportToolbar.viewsButtonItem
        implicitWidth:       220
        padding:     4
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color:        Theme.AppTheme.surfaceRaised
            radius:       Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.divider
            border.width: 1
        }
        
        Column {
            width: parent.width; spacing: 2

            Repeater {
                model: ["All Activity", "Updates", "Diagnostics", "Incidents", "Warnings"]

                delegate: Rectangle {
                    id: delegateRoot

                    required property string modelData
                    required property int    index
                    width:  parent.width; height: 34
                    radius: Theme.AppTheme.radiusMd
                    color:  _svMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                    AppControls.Label {
                        anchors {
                            left:           parent.left
                            leftMargin:     Theme.AppTheme.spacingMd
                            verticalCenter: parent.verticalCenter
                        }
                        text:           delegateRoot.modelData
                        color:          Theme.AppTheme.textPrimary
                        font.family:    Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                    }

                    MouseArea {
                        id: _svMA
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape:  Qt.PointingHandCursor
                        onClicked:    supportViewsPopup.close()
                    }
                }
            }
        }
    }
}

