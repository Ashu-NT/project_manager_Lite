pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Approval request detail page.
// Sections: Overview, Request Payload, Decision History, Audit.
// Approve / Reject actions appear ONLY on Overview (section-aware rule).
// Delegate is intentionally absent — requires backend API (controller/presenter/desktop-API).
Item {
    id: root

    property var approval: ({})
    property bool busy: false
    property string errorMessage: ""
    property string feedbackMessage: ""
    property int activeSectionIndex: 0

    signal backRequested()
    signal approveRequested(var item)
    signal rejectRequested(var item)

    readonly property string _title:         String(root.approval.title || "Request")
    readonly property string _status:        String(root.approval.statusLabel || "")
    readonly property string _submittedBy:   String(root.approval.subtitle || "")
    readonly property string _moduleSource:  String(root.approval.metaText || "")
    readonly property string _context:       String(root.approval.supportingText || "")
    readonly property string _requestId:     String(root.approval.id || "")
    readonly property bool   _isPending: {
        const s = root._status.toLowerCase()
        return s.includes("pending") || s.includes("awaiting")
    }

    readonly property var _sections: [
        { "label": "Overview" },
        { "label": "Request Payload" },
        { "label": "Decision History" },
        { "label": "Audit" }
    ]
    readonly property string _activeSectionLabel: {
        const s = root._sections[root.activeSectionIndex]
        return s ? String(s.label || "") : "Overview"
    }
    readonly property string _toolbarSubtitle: {
        switch (root._activeSectionLabel) {
        case "Overview":          return root._status
        case "Request Payload":   return "The data payload submitted with this change request."
        case "Decision History":  return "Previous decisions and notes recorded for this request."
        case "Audit":             return "Approval lifecycle events in the shared audit trail."
        default:                  return ""
        }
    }
    readonly property var _toolbarActions: {
        if (root._activeSectionLabel === "Overview" && root._isPending) {
            return [
                { "id": "approve", "label": "Approve", "icon": "approve", "enabled": true, "danger": false },
                { "id": "reject",  "label": "Reject",  "icon": "reject",  "enabled": true, "danger": true  }
            ]
        }
        if (root._activeSectionLabel === "Audit") {
            return [ { "id": "show_audit", "label": "Open Audit", "icon": "chevron_right" } ]
        }
        return []
    }

    readonly property var _overviewFields: [
        { "label": "Submitted by",  "value": root._submittedBy },
        { "label": "Module / Source", "value": root._moduleSource },
        { "label": "Status",        "value": root._status },
        { "label": "Context",       "value": root._context },
        { "label": "Request ID",    "value": root._requestId }
    ]

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

        AppWidgets.InlineMessage {
            width: parent ? parent.width : root.width
            visible: root.errorMessage.length > 0
            tone: "danger"
            message: root.errorMessage
        }

        AppWidgets.InlineMessage {
            width: parent ? parent.width : root.width
            visible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
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
                if (actionId === "approve") root.approveRequested(root.approval)
                else if (actionId === "reject") root.rejectRequested(root.approval)
            }
        }

        // ── Overview ───────────────────────────────────────────────
        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 0 ? _ovLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: _ovLoader
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                active: root.activeSectionIndex === 0
                keepLoaded: true
                loadingMessage: "Loading request overview..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0

                        AppWidgets.SectionHeading { width: parent.width; label: "Overview" }

                        Item {
                            width: parent.width
                            implicitHeight: _ovCol.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: _ovCol
                                anchors { top: parent.top; left: parent.left; right: parent.right
                                    topMargin: Theme.AppTheme.spacingMd
                                    leftMargin: Theme.AppTheme.spacingMd
                                    rightMargin: Theme.AppTheme.spacingMd }
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: _ovGrid.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Request Summary"
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
                                                id: _f
                                                required property var modelData
                                                Layout.fillWidth: true; spacing: 2
                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: String(_f.modelData.label || "")
                                                    color: Theme.AppTheme.textMuted
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    font.bold: true
                                                }
                                                AppControls.Label {
                                                    Layout.fillWidth: true
                                                    text: _f.modelData.value === undefined || _f.modelData.value === null || String(_f.modelData.value).length === 0
                                                        ? "-" : String(_f.modelData.value)
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

        // ── Request Payload ────────────────────────────────────────
        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 1 ? _payloadLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: _payloadLoader
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                active: root.activeSectionIndex === 1
                keepLoaded: true
                loadingMessage: "Loading payload..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0
                        AppWidgets.SectionHeading { width: parent.width; label: "Request Payload" }
                        Item {
                            width: parent.width
                            implicitHeight: _payloadCol.implicitHeight + Theme.AppTheme.spacingMd * 2
                            ColumnLayout {
                                id: _payloadCol
                                anchors { top: parent.top; left: parent.left; right: parent.right
                                    topMargin: Theme.AppTheme.spacingMd
                                    leftMargin: Theme.AppTheme.spacingMd
                                    rightMargin: Theme.AppTheme.spacingMd }
                                spacing: Theme.AppTheme.spacingMd

                                AppWidgets.InlineMessage {
                                    Layout.fillWidth: true
                                    tone: "info"
                                    message: "Full change payload visibility is governed by the shared approval workflow service. Deep payload inspection is available in the Audit workspace."
                                }

                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: _payloadBody.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Payload Summary"
                                    outlined: true
                                    ColumnLayout {
                                        id: _payloadBody
                                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.AppTheme.marginMd }
                                        spacing: Theme.AppTheme.spacingSm
                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: root._context.length > 0 ? root._context : "No payload context is available for this request."
                                            color: Theme.AppTheme.textSecondary
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

        // ── Decision History ───────────────────────────────────────
        Item {
            width: parent ? parent.width : root.width
            implicitHeight: root.activeSectionIndex === 2 ? _historyLoader.implicitHeight : 0
            height: implicitHeight
            visible: implicitHeight > 0

            AppWidgets.LazySectionLoader {
                id: _historyLoader
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                active: root.activeSectionIndex === 2
                keepLoaded: true
                loadingMessage: "Loading decision history..."
                sourceComponent: Component {
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0
                        AppWidgets.SectionHeading { width: parent.width; label: "Decision History" }
                        Item {
                            width: parent.width
                            implicitHeight: _histCol.implicitHeight + Theme.AppTheme.spacingMd * 2
                            ColumnLayout {
                                id: _histCol
                                anchors { top: parent.top; left: parent.left; right: parent.right
                                    topMargin: Theme.AppTheme.spacingMd
                                    leftMargin: Theme.AppTheme.spacingMd
                                    rightMargin: Theme.AppTheme.spacingMd }
                                spacing: Theme.AppTheme.spacingMd
                                AppWidgets.InlineMessage {
                                    Layout.fillWidth: true
                                    tone: "info"
                                    message: "Decision history is recorded in the shared approval workflow service and the platform audit trail."
                                }
                                AppWidgets.SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: _histBody.implicitHeight + Theme.AppTheme.spacingMd * 2
                                    title: "Decision Notes"
                                    outlined: true
                                    ColumnLayout {
                                        id: _histBody
                                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.AppTheme.marginMd }
                                        spacing: Theme.AppTheme.spacingSm
                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: root._isPending
                                                ? "No decision has been recorded yet — this request is awaiting your action."
                                                : "A decision has been recorded. See the Audit section for the full event record."
                                            color: Theme.AppTheme.textSecondary
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
                    Column {
                        width: parent ? parent.width : 0
                        spacing: 0
                        AppWidgets.SectionHeading { width: parent.width; label: "Audit" }
                        Item {
                            width: parent.width
                            implicitHeight: _auditCol.implicitHeight + Theme.AppTheme.spacingMd * 2
                            ColumnLayout {
                                id: _auditCol
                                anchors { top: parent.top; left: parent.left; right: parent.right
                                    topMargin: Theme.AppTheme.spacingMd
                                    leftMargin: Theme.AppTheme.spacingMd
                                    rightMargin: Theme.AppTheme.spacingMd }
                                spacing: Theme.AppTheme.spacingMd
                                AppWidgets.InlineMessage {
                                    Layout.fillWidth: true
                                    tone: "info"
                                    message: "Approval lifecycle events are centralized in the shared audit trail. Use Control Center → Audit for full event history."
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
