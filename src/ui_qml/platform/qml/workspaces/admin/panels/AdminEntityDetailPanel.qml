pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Platform.Widgets 1.0 as PlatformWidgets

Rectangle {
    id: root

    property string activeSection: ""
    property var detailItem: null
    property string selectedRowId: ""
    property var selectedDocument: ({
        "hasSelection": false, "documentId": "", "title": "Select a document",
        "summary": "", "badges": [], "metadataRows": [], "notes": ""
    })
    property var documentPreviewState: ({
        "statusLabel": "No document selected", "summary": "",
        "canOpen": false, "openLabel": "Open Source", "openTargetUrl": ""
    })
    property var documentLinkCatalog: ({
        "title": "Linked Records", "subtitle": "", "emptyState": "", "items": []
    })
    property var workspaceController: null
    property bool busy: false

    signal closeRequested()
    signal editRequested(string sectionId, string itemId)
    signal setActiveOrganizationRequested(string itemId)
    signal toggleEntityRequested(string sectionId, string itemId)
    signal documentLinkCreateRequested()
    signal documentEditRequested(string itemId)

    color: Theme.AppTheme.surface

    Rectangle {
        anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
        width: 1; color: Theme.AppTheme.divider
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Panel header ──────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: Theme.AppTheme.toolbarHeight - 6
            color: Theme.AppTheme.surfaceRaised

            Rectangle {
                anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                height: 1; color: Theme.AppTheme.divider
            }

            AppControls.Label {
                anchors.left: parent.left
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: _closeBtn.left
                anchors.rightMargin: 4
                text: root.detailItem ? (root.detailItem.title || "Details") : "Details"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
                elide: Text.ElideRight
            }

            Rectangle {
                id: _closeBtn
                anchors.right: parent.right
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                width: 26; height: 26; radius: 4
                color: _closeMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                AppIcons.AppIcon {
                    anchors.centerIn: parent
                    name: "close"; size: 10
                    iconColor: Theme.AppTheme.textMuted
                }

                MouseArea {
                    id: _closeMA
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.closeRequested()
                }
            }
        }

        // ── Panel body (scrollable) ───────────────────────────────────────
        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: _panelContent.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: _panelContent
                width: parent.width
                spacing: 0

                // ── Document inspector ────────────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.activeSection === "documents"
                    spacing: 0

                    PlatformWidgets.DocumentDetailPanel {
                        Layout.fillWidth: true
                        details: root.selectedDocument
                        previewState: root.documentPreviewState
                        actionsEnabled: root.workspaceController
                            ? !root.workspaceController.isBusy : false
                        onOpenRequested: function(url) {
                            if (url && url.length > 0) Qt.openUrlExternally(url)
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1; color: Theme.AppTheme.divider
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.AppTheme.marginMd
                        Layout.rightMargin: Theme.AppTheme.marginMd
                        Layout.topMargin: Theme.AppTheme.spacingSm
                        Layout.bottomMargin: Theme.AppTheme.spacingXs
                        spacing: Theme.AppTheme.spacingXs

                        AppControls.PrimaryButton {
                            Layout.fillWidth: true
                            text: "Edit"
                            iconName: "edit"
                            enabled: root.workspaceController ? !root.workspaceController.isBusy : false
                            onClicked: root.documentEditRequested(root.selectedRowId)
                        }

                        AppControls.SecondaryButton {
                            text: "Toggle"
                            iconName: "approve"
                            enabled: root.workspaceController ? !root.workspaceController.isBusy : false
                            onClicked: {
                                if (root.workspaceController)
                                    root.workspaceController.toggleDocumentActive(root.selectedRowId)
                            }
                        }
                    }

                    AppControls.SecondaryButton {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.AppTheme.marginMd
                        Layout.rightMargin: Theme.AppTheme.marginMd
                        Layout.bottomMargin: Theme.AppTheme.spacingSm
                        text: "Delete"
                        iconName: "delete"
                        danger: true
                        enabled: root.workspaceController ? !root.workspaceController.isBusy : false
                        onClicked: {}
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 1; color: Theme.AppTheme.divider
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.AppTheme.marginMd
                        Layout.rightMargin: Theme.AppTheme.marginMd
                        Layout.topMargin: Theme.AppTheme.spacingSm
                        Layout.bottomMargin: Theme.AppTheme.spacingSm
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: "Linked Records"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }

                        AppControls.Label {
                            visible: (root.documentLinkCatalog.items || []).length > 0
                            text: String((root.documentLinkCatalog.items || []).length)
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                        }

                        AppControls.SecondaryButton {
                            text: "Add Link"
                            iconName: "add"
                            enabled: root.selectedDocument.hasSelection
                                && (root.workspaceController ? !root.workspaceController.isBusy : false)
                            onClicked: root.documentLinkCreateRequested()
                        }
                    }

                    Repeater {
                        model: root.documentLinkCatalog.items || []

                        delegate: Rectangle {
                            id: delegateRoot
                            required property var modelData
                            required property int index
                            width: _panelContent.width
                            height: 34
                            color: _linkRowMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

                            Rectangle {
                                anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                                height: 1; color: Theme.AppTheme.divider
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.AppTheme.marginMd
                                anchors.rightMargin: Theme.AppTheme.marginSm
                                spacing: Theme.AppTheme.spacingXs

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: delegateRoot.modelData.title || ""
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    elide: Text.ElideRight
                                }

                                Rectangle {
                                    Layout.preferredWidth: 22; Layout.preferredHeight: 22; radius: 4
                                    color: _removeLinkMA.containsMouse ? Theme.AppTheme.dangerSoft : "transparent"

                                    AppIcons.AppIcon {
                                        anchors.centerIn: parent
                                        name: "close"; size: 9
                                        iconColor: _removeLinkMA.containsMouse
                                            ? Theme.AppTheme.danger : Theme.AppTheme.textMuted
                                    }

                                    MouseArea {
                                        id: _removeLinkMA
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        enabled: root.workspaceController ? !root.workspaceController.isBusy : false
                                        onClicked: {
                                            if (root.workspaceController)
                                                root.workspaceController.removeDocumentLink(delegateRoot.modelData.id)
                                        }
                                    }
                                }
                            }

                            MouseArea {
                                id: _linkRowMA
                                anchors.fill: parent
                                hoverEnabled: true
                            }
                        }
                    }
                }

                // ── Generic entity inspector ──────────────────────────────
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.margins: Theme.AppTheme.marginMd
                    visible: root.activeSection !== "documents"
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: root.detailItem ? (root.detailItem.title || "") : ""
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.sectionSize
                        font.bold: true
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    AppWidgets.StatusChip {
                        visible: root.detailItem ? (root.detailItem.statusLabel || "").length > 0 : false
                        status: root.detailItem ? (root.detailItem.statusLabel || "") : ""
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.topMargin: 2; Layout.bottomMargin: 2
                        height: 1; color: Theme.AppTheme.divider
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: root.detailItem ? (root.detailItem.subtitle || "").length > 0 : false

                        AppControls.Label { text: "Details"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root.detailItem ? (root.detailItem.subtitle || "") : ""
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        visible: root.detailItem ? (root.detailItem.metaText || "").length > 0 : false

                        AppControls.Label { text: "Info"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root.detailItem ? (root.detailItem.metaText || "") : ""
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.topMargin: 2
                        height: 1; color: Theme.AppTheme.divider
                        visible: root.detailItem !== null
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs
                        visible: root.detailItem !== null

                        AppControls.PrimaryButton {
                            Layout.fillWidth: true
                            text: "Edit"
                            iconName: "edit"
                            enabled: !root.busy
                            onClicked: root.editRequested(root.activeSection, root.selectedRowId)
                        }

                        AppControls.SecondaryButton {
                            visible: root.activeSection === "organizations"
                            text: "Set Active"
                            iconName: "approve"
                            enabled: !root.busy
                            onClicked: root.setActiveOrganizationRequested(root.selectedRowId)
                        }

                        AppControls.SecondaryButton {
                            visible: root.activeSection !== "organizations"
                            text: "Toggle"
                            iconName: "approve"
                            enabled: !root.busy
                            onClicked: root.toggleEntityRequested(root.activeSection, root.selectedRowId)
                        }
                    }

                    AppControls.SecondaryButton {
                        Layout.fillWidth: true
                        visible: root.detailItem !== null
                        text: "Delete"
                        iconName: "delete"
                        danger: true
                        enabled: !root.busy
                        onClicked: {}
                    }
                }
            }
        }
    }
}
