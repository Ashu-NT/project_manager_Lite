pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var resourceDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "",
        "emptyState": "Select a resource from the pool to review details or edit its setup.",
        "fields": [], "state": {}
    })
    property bool isBusy: false

    readonly property bool _hasResource: String(root.resourceDetail.id || "").length > 0
    readonly property string _workerType: String((root.resourceDetail.state || {}).workerType || "EXTERNAL")
    readonly property bool _isEmployeeBacked: root._workerType === "EMPLOYEE"

    function _sv(key) {
        const s = root.resourceDetail.state || {}
        return String(s[key] || "")
    }

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            width: parent.width
            title: root._hasResource ? root.resourceDetail.title : "Overview"
            subtitle: root._hasResource
                ? (root.resourceDetail.subtitle || root._sv("role") || "Resource details and configuration")
                : ""
            busy: root.isBusy
            actions: []
        }

        Item { width: parent.width; implicitHeight: Theme.AppTheme.spacingMd }

        AppWidgets.EmptyState {
            width: parent.width
            visible: !root._hasResource
            title: "No resource selected"
            message: root.resourceDetail.emptyState
                || "Select a resource from the pool to review details or edit its setup."
        }

        ColumnLayout {
            visible: root._hasResource
            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: root._isEmployeeBacked
                tone: "info"
                message: "Employee-backed resource. Identity fields (name, role, contact) are inherited from the Platform Employee record and are read-only in the editor."
            }

            AppWidgets.SectionCard {
                Layout.fillWidth: true
                title: "Resource Profile"
                outlined: true
                implicitHeight: _profileGrid.implicitHeight + Theme.AppTheme.spacingMd * 2

                GridLayout {
                    id: _profileGrid
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.marginMd
                    columns: 2
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing: Theme.AppTheme.spacingSm

                    Repeater {
                        model: [
                            { "label": "Role",        "value": root._sv("role") || "-" },
                            { "label": "Worker Type",  "value": root._sv("workerTypeLabel") || "-" },
                            { "label": "Hourly Rate",  "value": root._sv("hourlyRateLabel") || "-" },
                            { "label": "Cost Type",    "value": root._sv("costTypeLabel") || "-" },
                            { "label": "Contact",      "value": root._sv("contact") || "-" },
                            { "label": "Currency",     "value": root._sv("currency") || "-" }
                        ]

                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(modelData.value || "-")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.StatusChip { status: root.resourceDetail.statusLabel || "" }

                AppControls.Label {
                    visible: root._sv("version").length > 0
                    text: "v" + root._sv("version")
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }

                Item { Layout.fillWidth: true }
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: String(root.resourceDetail.description || "").length > 0
                text: root.resourceDetail.description || ""
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
                maximumLineCount: 4
                elide: Text.ElideRight
            }

            Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }
        }

        Item { width: parent.width; implicitHeight: Theme.AppTheme.spacingMd }
    }
}
