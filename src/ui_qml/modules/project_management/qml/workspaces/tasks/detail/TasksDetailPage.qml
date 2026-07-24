pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "." as DetailComponents

AppWidgets.SectionDetailPage {
    id: root

    // ── Input properties ─────────────────────────────────────────────────
    property var state: null
    property var workspaceController: null
    property var selectedTaskModel: ({})
    property var detailPanel: null

    // ── Signals ──────────────────────────────────────────────────────────
    signal backRequested()
    signal editRequested()
    signal progressRequested()
    signal deleteRequested()
    signal reserveMaterialRequested()

    // ── Configuration ────────────────────────────────────────────────────
    open: true
    anchors.fill: parent
    showHeader: false
    showEdit: false
    showDelete: false
    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
    sections: root.state ? root.state.detailSections : []
    z: 20

    Component.onCompleted: {
        if (detailPanel && detailPanel.sectionIndex !== undefined) {
            scrollToSection(detailPanel.sectionIndex)
        }
    }

    onSectionChanged: function(index) {
        if (root.state) {
            root.state.lazyLoadDetailSection(root, index)
        }
    }

    // ── Detail header toolbar ────────────────────────────────────────────
    AppWidgets.ContextualActionToolbar {
        detailPagePinned: true
        width: parent ? parent.width : 0
        showBack: true
        title: root.selectedTaskModel.title || "Task Details"
        subtitle: root.selectedTaskModel.statusLabel || root.selectedTaskModel.subtitle || ""
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        actions: root.state ? root.state.detailActionsForSection(activeSectionIndex) : []

        onBackRequested: {
            root.backRequested()
        }
        onActionTriggered: function(actionId) {
            if (actionId === "edit") {
                root.editRequested()
            } else if (actionId === "progress") {
                root.progressRequested()
            } else if (actionId === "delete") {
                root.deleteRequested()
            } else if (actionId === "reserve_material") {
                root.reserveMaterialRequested()
            }
        }
    }

    // ── Detail error message ─────────────────────────────────────────────
    AppWidgets.SectionScopedInlineMessage {
        width: parent ? parent.width : 0
        requestedVisible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
        tone: "danger"
        message: root.workspaceController ? root.workspaceController.errorMessage : ""
    }

    // ── Detail success message ───────────────────────────────────────────
    AppWidgets.SectionScopedInlineMessage {
        width: parent ? parent.width : 0
        requestedVisible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
            && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
        tone: "success"
        message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
    }

    // ── Detail panel (contains all sections) ──────────────────────────────
    // Embedded by parent - section content is provided by TasksDetailPanel
}
