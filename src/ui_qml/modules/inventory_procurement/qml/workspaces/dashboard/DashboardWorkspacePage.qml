pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers

AppLayouts.WorkspaceFrame {
    id: root

    property var platformCatalog
    property var _caps: ({})

    Component.onCompleted: {
        if (root.platformCatalog) {
            root._caps = root.platformCatalog.capabilitySnapshot()
        }
    }

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementDashboardWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.dashboardWorkspace
        : null
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": "Inventory Dashboard", "subtitle": "Inventory KPIs, stock health, procurement pressure, and movement activity.", "metrics": [] })

    title: root.overviewModel.title || "Inventory Dashboard"
    subtitle: root.overviewModel.subtitle || ""

    readonly property var _sections: root.workspaceController
        ? (root.workspaceController.sections || [])
        : []

    property int _activePanelIndex: 0

    readonly property var _panelColumns: [
        { "key": "title",        "label": "Item",     "flex": 2, "sortable": false },
        { "key": "subtitle",     "label": "Details",  "flex": 1.5 },
        { "key": "statusLabel",  "label": "Status",   "flex": 0, "minWidth": 90, "type": "status" },
        { "key": "metaText",     "label": "Location", "flex": 1 }
    ]

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        // ── KPI Strip ──────────────────────────────────────────────────────
        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        // ── Inline messages ────────────────────────────────────────────────
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "info"
            message: "Loading inventory dashboard..."
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "success"
            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        // ── Panel navigation tabs ─────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Theme.AppTheme.toolbarHeight
            color: Theme.AppTheme.surfaceRaised
            radius: Theme.AppTheme.radiusMd
            visible: root._sections.length > 0

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingXs

                Repeater {
                    model: root._sections

                    delegate: Rectangle {
                        id: panelTab
                        required property var modelData
                        required property int index

                        Layout.preferredHeight: Theme.AppTheme.toolbarHeight - 8
                        Layout.alignment: Qt.AlignVCenter
                        implicitWidth: panelTabLabel.implicitWidth + 24
                        radius: Theme.AppTheme.radiusSm
                        color: root._activePanelIndex === panelTab.index
                            ? Theme.AppTheme.accent
                            : (tabHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent")

                        AppControls.Label {
                            id: panelTabLabel
                            anchors.centerIn: parent
                            text: panelTab.modelData.title || ""
                            color: root._activePanelIndex === panelTab.index
                                ? Theme.AppTheme.accentForeground
                                : Theme.AppTheme.textSecondary
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: root._activePanelIndex === panelTab.index
                            font.family: Theme.AppTheme.fontFamily
                        }

                        HoverHandler { id: tabHover }
                        TapHandler {
                            onTapped: root._activePanelIndex = panelTab.index
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    visible: root.workspaceController !== null
                    implicitWidth: refreshRow.implicitWidth + 16
                    implicitHeight: Theme.AppTheme.inputHeight - 4
                    radius: Theme.AppTheme.radiusSm
                    color: refreshHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                    RowLayout {
                        id: refreshRow
                        anchors.centerIn: parent
                        spacing: 4

                        AppControls.Label {
                            text: "Refresh"
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.family: Theme.AppTheme.fontFamily
                        }
                    }

                    HoverHandler { id: refreshHover }
                    TapHandler {
                        onTapped: {
                            if (root.workspaceController !== null) {
                                root.workspaceController.refresh()
                            }
                        }
                    }
                }
            }
        }

        // ── Active panel ──────────────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            visible: root._sections.length > 0

            readonly property var _activeSection: root._sections[root._activePanelIndex] || ({
                "title": "",
                "subtitle": "",
                "emptyState": "Select a panel above.",
                "rows": []
            })

            AppWidgets.DataTable {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                columns: root._panelColumns
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: parent._activeSection.emptyState || "No records in this panel."
                multiSelect: false
            }
        }

        // ── Empty state when no sections ──────────────────────────────────
        AppWidgets.EmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root._sections.length === 0 && !(root.workspaceController ? root.workspaceController.isLoading : false)
            title: root.workspaceController ? root.workspaceController.emptyState : "Inventory dashboard data not yet available."
        }
    }
}
