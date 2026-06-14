pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Dialogs 1.0 as PlatformDialogs
import "../../admin/components"

// Module Entitlement detail page — follows the Admin list/detail pattern.
// Sections: Overview, Capabilities, Consumers, Audit.
// Entity-level actions (Lifecycle / Licensed / Enabled) appear ONLY on Overview.
// The ModuleLifecycleDialog is owned here to keep dialog state local.
Item {
    id: root

    property var module: ({})
    property var lifecycleOptions: []
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal lifecycleChangeRequested(string moduleCode, string lifecycleStatus)
    signal toggleLicensedRequested(string moduleCode)
    signal toggleEnabledRequested(string moduleCode)

    readonly property string _title:    String(root.module.title || "Module")
    readonly property string _status:   String(root.module.statusLabel || "")
    readonly property string _subtitle: String(root.module.subtitle || "")
    readonly property string _runtime:  String(root.module.metaText || "")
    readonly property string _moduleCode: String(
        (root.module.state && root.module.state.moduleCode) ? root.module.state.moduleCode
        : (root.module.id || "")
    )
    readonly property bool _canLifecycle: !!(root.module.canTertiaryAction)
    readonly property bool _canLicensed:  !!(root.module.canPrimaryAction)
    readonly property bool _canEnabled:   !!(root.module.canSecondaryAction)

    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Capabilities" },
        { "label": "Consumers" },
        { "label": "Audit" }
    ]

    readonly property string _activeSectionLabel: {
        const s = root._sections[root.activeSectionIndex]
        return s ? String(s.label || "") : "Overview"
    }

    readonly property string _toolbarSubtitle: {
        switch (root._activeSectionLabel) {
        case "Overview":     return root._subtitle
        case "Capabilities": return "Integration capabilities this module provides or consumes."
        case "Consumers":    return "Other modules and services that depend on this module."
        case "Audit":        return "Module lifecycle and entitlement change history."
        default:             return ""
        }
    }

    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview") {
            return [
                { "id": "lifecycle", "label": "Lifecycle", "icon": "settings", "enabled": root._canLifecycle },
                { "id": "licensed",  "label": "Licensed",  "icon": "approve",  "enabled": root._canLicensed  },
                { "id": "enabled",   "label": "Enabled",   "icon": "approve",  "enabled": root._canEnabled   }
            ]
        }
        if (root._activeSectionLabel === "Audit") {
            return [ { "id": "show_audit", "label": "Open Audit", "icon": "chevron_right" } ]
        }
        return [ { "id": "refresh", "label": "Refresh", "icon": "refresh" } ]
    }

    readonly property var _overviewFields: [
        { "label": "Module",        "value": root._title },
        { "label": "Stage/License", "value": root._subtitle },
        { "label": "Lifecycle",     "value": root._status },
        { "label": "Runtime",       "value": root._runtime },
        { "label": "Module Code",   "value": root._moduleCode }
    ]

    // ── Module lifecycle dialog (owned locally, state per-module) ──
    PlatformDialogs.ModuleLifecycleDialog {
        id: lifecycleDialog
        onStatusConfirmed: function(moduleCode, lifecycleStatus) {
            root.lifecycleChangeRequested(moduleCode, lifecycleStatus)
            lifecycleDialog.close()
        }
    }

    AppWidgets.SectionDetailPage {
        id: detailPage
        anchors.fill: parent
        open: true
        title: root._title
        isBusy: root.busy
        showEdit: false
        showDelete: false
        sections: root._sections

        onBackRequested: root.backRequested()
        onSectionChanged: function(index) { root.activeSectionIndex = index }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : root.width
            requestedVisible: root.errorMessage.length > 0
            tone: "danger"
            message: root.errorMessage
        }

        AppWidgets.SectionScopedInlineMessage {
            width: parent ? parent.width : root.width
            requestedVisible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
            tone: "success"
            message: root.feedbackMessage
        }

        AppWidgets.ContextualActionToolbar {
            detailPagePinned: true
            width: parent ? parent.width : root.width
            title: root._activeSectionLabel
            subtitle: root._toolbarSubtitle
            busy: root.busy
            actions: root._toolbarActions
            onActionTriggered: function(actionId) {
                if (actionId === "lifecycle") {
                    lifecycleDialog.openForItem(root.module, root.lifecycleOptions)
                } else if (actionId === "licensed") {
                    root.toggleLicensedRequested(root._moduleCode)
                } else if (actionId === "enabled") {
                    root.toggleEnabledRequested(root._moduleCode)
                }
            }
        }

        // ── Overview ───────────────────────────────────────────────
        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 0 ? _overviewLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: _overviewLoader
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                active: root.activeSectionIndex === 0
                keepLoaded: true
                loadingMessage: "Loading module overview..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading { width: parent.width; label: "Overview" }

                        Item {
                            width: parent.width
                            implicitHeight: _ovColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: _ovColumn
                                anchors { top: parent.top; left: parent.left; right: parent.right
                                    topMargin: Theme.AppTheme.spacingMd
                                    leftMargin: Theme.AppTheme.spacingMd
                                    rightMargin: Theme.AppTheme.spacingMd }
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: _ovGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Module Summary"
                                    outlined: true

                                    GridLayout {
                                        id: _ovGrid
                                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.AppTheme.marginMd }
                                        columns: 2
                                        columnSpacing: Theme.AppTheme.spacingLg
                                        rowSpacing: Theme.AppTheme.spacingSm

                                        Repeater {
                                            model: root._overviewFields
                                            delegate: ColumnLayout {
                                                id: _fld
                                                required property var modelData
                                                Layout.fillWidth: true; spacing: 2
                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: String(_fld.modelData.label || "")
                                                    color: Theme.AppTheme.textMuted
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    font.bold: true
                                                }
                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: _fld.modelData.value === undefined || _fld.modelData.value === null || String(_fld.modelData.value).length === 0
                                                        ? "-" : String(_fld.modelData.value)
                                                    color: Theme.AppTheme.textPrimary
                                                    font.pixelSize: Theme.AppTheme.smallSize
                                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── Capabilities ───────────────────────────────────────────
        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 1 ? _capLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: _capLoader
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                active: root.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading capabilities..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Capabilities"
                        infoMessage: "Integration capabilities are governed by the Platform Integration Capabilities workspace. Navigate there for provider/consumer detail."
                        cardTitle: "Integration Boundary"
                        notes: [
                            "This module's capabilities are visible in Settings → Integration Capabilities.",
                            "Capability state is managed at the platform level, not per-module detail."
                        ]
                    }
                }
            }
        }

        // ── Consumers ──────────────────────────────────────────────
        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 2 ? _consumersLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: _consumersLoader
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                active: root.activeSectionIndex === 2
                keepLoaded: true
                loadingMessage: "Loading consumers..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Consumers"
                        infoMessage: "Consumer relationships between modules are governed by the shared integration capability registry."
                        cardTitle: "Consumer Boundary"
                        notes: [
                            "Module consumer graphs are managed at the platform level.",
                            "Disabling a module may affect downstream consumers — review capabilities before changing lifecycle state."
                        ]
                    }
                }
            }
        }

        // ── Audit ──────────────────────────────────────────────────
        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 3 ? _auditLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: _auditLoader
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                active: root.activeSectionIndex === 3
                keepLoaded: true
                loadingMessage: "Loading audit guidance..."
                sourceComponent: Component {
                    AdminInformationalDetailSection {
                        sectionLabel: "Audit"
                        infoMessage: "Module lifecycle and entitlement change history is centralized in the shared audit workspace."
                        cardTitle: "Audit Boundary"
                        notes: [
                            "Use the Control Center → Audit workspace for lifecycle change history.",
                            "Module entitlement events are recorded in the shared platform audit trail."
                        ]
                    }
                }
            }
        }
    }
}
