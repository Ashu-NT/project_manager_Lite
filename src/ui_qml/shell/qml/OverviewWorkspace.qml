pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import App.Controls 1.0 as AppControls

// The Global Overview landing page. Every section (context, attention,
// modules, recent activity, action center, quick actions) binds to its own
// independent GlobalOverviewController property + *State pair -- one
// section loading/failing never blocks or hides the others. `controller`
// arrives from the shell's Loader-based property injection (see
// MainWindow.qml), the same mechanism shellModel/platformCatalog/pmCatalog
// already use -- so it is null when this page is loaded standalone (e.g.
// the offscreen route sweep), and every binding below is null-safe.
AppLayouts.WorkspaceFrame {
    id: root

    property var globalOverviewController: null

    title: "Overview"
    subtitle: "Monitor your organization, access business modules, and continue your work."

    readonly property string _layoutClass: Theme.AppTheme.layoutClassFor(Window.width, Window.height)
    readonly property bool _narrow: root._layoutClass === "narrow"
    readonly property bool _compact: root._layoutClass === "compact"
    // Section/card spacing tightens for compact AND narrow (both are
    // constrained); only the column/grid arrangement itself is narrow-only.
    readonly property bool _tightSpacing: root._narrow || root._compact

    readonly property var _context: root.globalOverviewController ? (root.globalOverviewController.context || {}) : {}
    readonly property var _contextState: root.globalOverviewController ? (root.globalOverviewController.contextState || {}) : {}
    readonly property var _attention: root.globalOverviewController ? (root.globalOverviewController.attention || []) : []
    readonly property var _attentionState: root.globalOverviewController ? (root.globalOverviewController.attentionState || {}) : {}
    readonly property var _modules: root.globalOverviewController ? (root.globalOverviewController.modules || []) : []
    readonly property var _modulesState: root.globalOverviewController ? (root.globalOverviewController.modulesState || {}) : {}
    readonly property var _recentActivity: root.globalOverviewController ? (root.globalOverviewController.recentActivity || []) : []
    readonly property var _recentActivityState: root.globalOverviewController ? (root.globalOverviewController.recentActivityState || {}) : {}
    readonly property var _actionCenter: root.globalOverviewController ? (root.globalOverviewController.actionCenter || []) : []
    readonly property var _actionCenterState: root.globalOverviewController ? (root.globalOverviewController.actionCenterState || {}) : {}
    readonly property var _quickActions: root.globalOverviewController ? (root.globalOverviewController.quickActions || []) : []

    property bool _hasTriggeredInitialLoad: false

    function _selectRoute(routeId) {
        if (root.globalOverviewController && routeId && routeId.length > 0) {
            root.globalOverviewController.selectRoute(routeId)
        }
    }

    function _triggerInitialLoadIfReady() {
        if (root.globalOverviewController && !root._hasTriggeredInitialLoad) {
            root._hasTriggeredInitialLoad = true
            root.globalOverviewController.reload()
        }
    }

    onGlobalOverviewControllerChanged: root._triggerInitialLoadIfReady()
    Component.onCompleted: root._triggerInitialLoadIfReady()

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: _content.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        ColumnLayout {
            id: _content
            width: parent.width
            spacing: root._tightSpacing ? Theme.AppTheme.spacingLg : Theme.AppTheme.sectionGap

            // -- Context line ------------------------------------------------
            AppControls.Label {
                Layout.fillWidth: true
                visible: String(root._context.contextLine || "").length > 0
                text: String(root._context.contextLine || "")
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
            }

            // -- Attention -----------------------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm
                visible: !!root._attentionState.loading
                    || String(root._attentionState.errorMessage || "").length > 0
                    || root._attention.length > 0

                AppControls.Label {
                    text: "Needs your attention"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.sectionSize
                    font.bold: true
                }

                AppWidgets.LoadingOverlay {
                    Layout.fillWidth: true
                    compact: true
                    loading: !!root._attentionState.loading
                    message: "Loading attention summary…"
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    tone: "danger"
                    message: String(root._attentionState.errorMessage || "")
                }

                GridLayout {
                    Layout.fillWidth: true
                    visible: !root._attentionState.loading && String(root._attentionState.errorMessage || "").length === 0
                    columns: root._narrow ? 2 : 4
                    columnSpacing: Theme.AppTheme.spacingMd
                    rowSpacing: Theme.AppTheme.spacingMd

                    Repeater {
                        model: root._attention

                        delegate: AppWidgets.OverviewMetricTile {
                            id: _tile
                            required property var modelData

                            Layout.fillWidth: true
                            label: String(_tile.modelData.label || "")
                            value: String(_tile.modelData.value !== undefined ? _tile.modelData.value : "--")
                            supportingText: String(_tile.modelData.supportingText || "")
                            // Attention cards are informational only in this
                            // release -- no dedicated Action Center
                            // destination exists yet to navigate them to.
                            clickable: false
                            compact: root._compact
                        }
                    }
                }
            }

            // -- Quick actions -----------------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm
                // Hidden entirely when there are zero verified actions --
                // never a row of disabled/dead buttons.
                visible: root._quickActions.length > 0

                AppControls.Label {
                    text: "Quick actions"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.sectionSize
                    font.bold: true
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: root._quickActions

                        delegate: AppControls.SecondaryButton {
                            id: _action
                            required property var modelData

                            text: String(_action.modelData.label || "")
                            iconName: String(_action.modelData.icon || "")
                            onClicked: root._selectRoute(String(_action.modelData.routeId || ""))
                        }
                    }
                }
            }

            // -- Modules -----------------------------------------------------
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm
                visible: !!root._modulesState.loading
                    || String(root._modulesState.errorMessage || "").length > 0
                    || root._modules.length > 0

                AppControls.Label {
                    text: "Modules"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.sectionSize
                    font.bold: true
                }

                AppWidgets.LoadingOverlay {
                    Layout.fillWidth: true
                    compact: true
                    loading: !!root._modulesState.loading
                    message: "Loading modules…"
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    tone: "danger"
                    message: String(root._modulesState.errorMessage || "")
                }

                GridLayout {
                    Layout.fillWidth: true
                    visible: !root._modulesState.loading && String(root._modulesState.errorMessage || "").length === 0
                    columns: root._narrow ? 1 : 2
                    columnSpacing: Theme.AppTheme.spacingMd
                    rowSpacing: Theme.AppTheme.spacingMd

                    Repeater {
                        model: root._modules

                        delegate: AppWidgets.ModuleCard {
                            id: _card
                            required property var modelData

                            Layout.fillWidth: true
                            moduleCode: String(_card.modelData.moduleCode || "")
                            title: String(_card.modelData.title || "")
                            description: String(_card.modelData.description || "")
                            iconKey: String(_card.modelData.iconKey || "")
                            summaryText: String(_card.modelData.summaryText || "")
                            routeId: String(_card.modelData.routeId || "")
                            compact: root._compact
                            onActivated: root._selectRoute(_card.routeId)
                        }
                    }
                }
            }

            // -- Recent Activity / Action Center -------------------------------
            GridLayout {
                Layout.fillWidth: true
                columns: root._narrow ? 1 : 2
                columnSpacing: Theme.AppTheme.sectionGap
                rowSpacing: Theme.AppTheme.sectionGap

                // Recent Activity (~45% on standard/compact width)
                AppWidgets.SectionCard {
                    objectName: "overviewRecentActivityCard"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    Layout.preferredWidth: root._narrow ? -1 : Math.round((_content.width - Theme.AppTheme.sectionGap) * 0.45)
                    title: "Recent Activity"

                    ColumnLayout {
                        width: parent.width
                        spacing: Theme.AppTheme.spacingSm

                        AppWidgets.LoadingOverlay {
                            Layout.fillWidth: true
                            compact: true
                            loading: !!root._recentActivityState.loading
                            message: "Loading recent activity…"
                        }

                        AppWidgets.InlineMessage {
                            Layout.fillWidth: true
                            tone: "danger"
                            message: String(root._recentActivityState.errorMessage || "")
                        }

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: !root._recentActivityState.loading
                                && String(root._recentActivityState.errorMessage || "").length === 0
                                && root._recentActivityState.empty === true
                            title: "No recent activity"
                            message: "Business activity will appear here as work is completed across the organization."
                        }

                        AppWidgets.ActivityFeed {
                            id: _activityFeed
                            objectName: "overviewRecentActivityFeed"
                            Layout.fillWidth: true
                            visible: !root._recentActivityState.loading
                                && String(root._recentActivityState.errorMessage || "").length === 0
                                && root._recentActivity.length > 0
                            items: root._recentActivity
                        }
                    }
                }

                // Action Center (~55% on standard/compact width)
                AppWidgets.SectionCard {
                    objectName: "overviewActionCenterCard"
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    Layout.preferredWidth: root._narrow ? -1 : Math.round((_content.width - Theme.AppTheme.sectionGap) * 0.55)
                    title: "Action Center"

                    ColumnLayout {
                        width: parent.width
                        spacing: Theme.AppTheme.spacingSm

                        AppWidgets.LoadingOverlay {
                            Layout.fillWidth: true
                            compact: true
                            loading: !!root._actionCenterState.loading
                            message: "Loading action items…"
                        }

                        AppWidgets.InlineMessage {
                            Layout.fillWidth: true
                            tone: "danger"
                            message: String(root._actionCenterState.errorMessage || "")
                        }

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: !root._actionCenterState.loading
                                && String(root._actionCenterState.errorMessage || "").length === 0
                                && root._actionCenterState.empty === true
                            title: "You're all caught up"
                            message: "There are no action items requiring your attention."
                        }

                        AppWidgets.ActionCenterList {
                            id: _actionCenterList
                            objectName: "overviewActionCenterList"
                            Layout.fillWidth: true
                            visible: !root._actionCenterState.loading
                                && String(root._actionCenterState.errorMessage || "").length === 0
                                && root._actionCenter.length > 0
                            items: root._actionCenter
                            onItemActivated: function (item) {
                                root._selectRoute(String(item.routeId || ""))
                            }
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: Theme.AppTheme.spacingMd }
        }
    }
}
