pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var workspaceController: null
    property int bottomTab: 0
    property string selectedFundingId: ""

    property var intakeModel: ({ "emptyState": "No intake items available.", "items": [] })
    property var dependenciesModel: ({ "emptyState": "No cross-project dependencies recorded.", "items": [] })
    property var capacityPoolModel: ({
        "title": "Capacity Pool", "subtitle": "", "emptyState": "Assign resources to tasks to see portfolio-level capacity demand.", "items": []
    })
    property var templatesModel: ({
        "title": "Scoring Templates", "subtitle": "", "emptyState": "No scoring templates available.", "items": []
    })
    property var activityItems: []
    property var recentActionsModel: ({ "emptyState": "No recent portfolio activity." })

    signal bottomTabRequested(int tab)
    signal selectedFundingIdRequested(string fundingId)

    readonly property var _fundingColumns: [
        { "key": "title",          "label": "Intake Item",       "flex": 3, "minWidth": 160, "sortable": true },
        { "key": "statusLabel",    "label": "Status",            "flex": 1, "minWidth": 90,  "type": "status" },
        { "key": "subtitle",       "label": "Sponsor",           "flex": 2, "minWidth": 120 },
        { "key": "supportingText", "label": "Budget / Capacity", "flex": 2, "minWidth": 160 },
        { "key": "metaText",       "label": "Score",             "flex": 1, "minWidth": 60 }
    ]
    readonly property var _riskColumns: [
        { "key": "title",          "label": "Dependency", "flex": 3, "minWidth": 200 },
        { "key": "subtitle",       "label": "Type",        "flex": 1, "minWidth": 100 },
        { "key": "statusLabel",    "label": "Pressure",    "flex": 1, "minWidth": 80, "type": "status" },
        { "key": "supportingText", "label": "Status",      "flex": 2, "minWidth": 160 }
    ]

    color: Theme.AppTheme.surfaceRaised
    radius: Theme.AppTheme.radiusMd
    border.color: Theme.AppTheme.subtleBorder
    border.width: 1
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Tab strip ─────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 36
            color: Theme.AppTheme.surfaceAlt
            radius: Theme.AppTheme.radiusMd

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingXs

                Repeater {
                    model: ["Funding", "Risks", "Capacity", "Governance", "Activity"]

                    delegate: Rectangle {
                        id: _tabBtn
                        required property var modelData
                        required property int index

                        implicitWidth: _tabLabel.implicitWidth + 20
                        implicitHeight: 26
                        radius: Theme.AppTheme.radiusSm
                        color: root.bottomTab === _tabBtn.index
                            ? Theme.AppTheme.accent
                            : (_tabHover.containsMouse ? Theme.AppTheme.hoverSurface : Qt.rgba(0, 0, 0, 0))

                        AppControls.Label {
                            id: _tabLabel
                            anchors.centerIn: parent
                            text: String(_tabBtn.modelData || "")
                            color: root.bottomTab === _tabBtn.index ? "white" : Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: root.bottomTab === _tabBtn.index
                        }

                        MouseArea {
                            id: _tabHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.bottomTabRequested(_tabBtn.index)
                        }
                    }
                }

                Item { Layout.fillWidth: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        // ── Tab content ───────────────────────────────────────────────────
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.bottomTab

            // ── Tab 0: Funding ────────────────────────────────────────────
            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    AppWidgets.DataTable {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: root._fundingColumns
                        sourceModel: root.workspaceController ? root.workspaceController.intakeItemsTableModel : null
                        emptyText: root.intakeModel.emptyState || "No intake items available."
                        multiSelect: false
                        selectedRowId: root.selectedFundingId
                        onRowSelected: function(rowId) { root.selectedFundingIdRequested(rowId) }
                        onRowActivated: function(rowId) { root.selectedFundingIdRequested(rowId) }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        visible: root.selectedFundingId.length > 0
                        color: Theme.AppTheme.surfaceAlt

                        Rectangle {
                            anchors.top: parent.top
                            anchors.left: parent.left
                            anchors.right: parent.right
                            height: 1
                            color: Theme.AppTheme.divider
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.AppTheme.marginMd
                            anchors.rightMargin: Theme.AppTheme.marginMd
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: "Status:"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }

                            AppControls.SecondaryButton {
                                text: "Approve"
                                iconName: "approve"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                onClicked: {
                                    if (root.workspaceController !== null) {
                                        root.workspaceController.updateIntakeItemStatus(root.selectedFundingId, "APPROVED")
                                        root.selectedFundingIdRequested("")
                                    }
                                }
                            }

                            AppControls.SecondaryButton {
                                text: "Review"
                                iconName: "edit"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                onClicked: {
                                    if (root.workspaceController !== null) {
                                        root.workspaceController.updateIntakeItemStatus(root.selectedFundingId, "REVIEW")
                                        root.selectedFundingIdRequested("")
                                    }
                                }
                            }

                            AppControls.SecondaryButton {
                                text: "Reject"
                                iconName: "delete"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                onClicked: {
                                    if (root.workspaceController !== null) {
                                        root.workspaceController.updateIntakeItemStatus(root.selectedFundingId, "REJECTED")
                                        root.selectedFundingIdRequested("")
                                    }
                                }
                            }

                            Item { Layout.fillWidth: true }

                            AppControls.SecondaryButton {
                                text: "Clear"
                                onClicked: root.selectedFundingIdRequested("")
                            }
                        }
                    }
                }
            }

            // ── Tab 1: Risks ──────────────────────────────────────────────
            Item {
                AppWidgets.DataTable {
                    anchors.fill: parent
                    columns: root._riskColumns
                    sourceModel: root.workspaceController ? root.workspaceController.portfolioDependenciesTableModel : null
                    emptyText: root.dependenciesModel.emptyState || "No cross-project dependencies recorded."
                    onRowSelected: function(rowId) {}
                }
            }

            // ── Tab 2: Capacity ───────────────────────────────────────────
            Item {
                Flickable {
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: _capCol.implicitHeight + Theme.AppTheme.marginMd * 2
                    clip: true

                    ColumnLayout {
                        id: _capCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.leftMargin: Theme.AppTheme.marginMd
                        anchors.rightMargin: Theme.AppTheme.marginMd
                        anchors.topMargin: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingMd

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root.capacityPoolModel.title || "Capacity Pool"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root.capacityPoolModel.subtitle || ""
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.Wrap
                            visible: !!text
                        }

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: (root.capacityPoolModel.items || []).length === 0
                            title: "No capacity data"
                            message: root.capacityPoolModel.emptyState || "Assign resources to tasks to see portfolio-level capacity demand."
                        }

                        Repeater {
                            model: root.capacityPoolModel.items || []
                            delegate: Rectangle {
                                id: _capRow
                                required property var modelData
                                required property int index
                                Layout.fillWidth: true
                                implicitHeight: _capRowContent.implicitHeight + Theme.AppTheme.spacingSm * 2
                                color: (_capRow.modelData.state && _capRow.modelData.state.overloaded)
                                    ? Qt.rgba(Theme.AppTheme.danger.r, Theme.AppTheme.danger.g, Theme.AppTheme.danger.b, 0.08)
                                    : Theme.AppTheme.surfaceAlt
                                radius: Theme.AppTheme.radiusSm

                                RowLayout {
                                    id: _capRowContent
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: Theme.AppTheme.spacingSm
                                    spacing: Theme.AppTheme.spacingSm

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_capRow.modelData.title || "")
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        elide: Text.ElideRight
                                    }
                                    AppControls.Label {
                                        text: String(_capRow.modelData.subtitle || "")
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                    AppControls.Label {
                                        text: String(_capRow.modelData.statusLabel || "")
                                        color: (_capRow.modelData.state && _capRow.modelData.state.overloaded)
                                            ? Theme.AppTheme.danger : Theme.AppTheme.success
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold: true
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ── Tab 3: Governance ─────────────────────────────────────────
            Item {
                Flickable {
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: _govCol.implicitHeight + Theme.AppTheme.marginMd * 2
                    clip: true

                    ColumnLayout {
                        id: _govCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.leftMargin: Theme.AppTheme.marginMd
                        anchors.rightMargin: Theme.AppTheme.marginMd
                        anchors.topMargin: Theme.AppTheme.spacingSm
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root.templatesModel.title || "Scoring Templates"
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root.templatesModel.subtitle || ""
                            visible: text.length > 0
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }

                        Repeater {
                            model: root.templatesModel.items || []

                            delegate: Rectangle {
                                id: _tplRow
                                required property var modelData
                                Layout.fillWidth: true
                                height: _tplRowLayout.implicitHeight + 16
                                radius: Theme.AppTheme.radiusSm
                                color: Theme.AppTheme.surfaceAlt
                                border.color: Theme.AppTheme.subtleBorder
                                border.width: 1

                                RowLayout {
                                    id: _tplRowLayout
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 8
                                    spacing: Theme.AppTheme.spacingSm

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: String(_tplRow.modelData.title || "")
                                            color: Theme.AppTheme.textPrimary
                                            font.family: Theme.AppTheme.fontFamily
                                            font.pixelSize: Theme.AppTheme.smallSize
                                            font.bold: true
                                            elide: Text.ElideRight
                                        }

                                        AppControls.Label {
                                            Layout.fillWidth: true
                                            text: String(_tplRow.modelData.subtitle || "")
                                            color: Theme.AppTheme.textSecondary
                                            font.family: Theme.AppTheme.fontFamily
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            elide: Text.ElideRight
                                        }
                                    }

                                    AppWidgets.StatusChip {
                                        status: String(_tplRow.modelData.statusLabel || "")
                                    }

                                    AppControls.SecondaryButton {
                                        visible: Boolean(_tplRow.modelData.canPrimaryAction)
                                        text: "Activate"
                                        iconName: "approve"
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                        onClicked: {
                                            if (root.workspaceController !== null)
                                                root.workspaceController.activateTemplate(
                                                    String((_tplRow.modelData.state || {}).templateId || "")
                                                )
                                        }
                                    }
                                }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: (root.templatesModel.items || []).length === 0
                            text: root.templatesModel.emptyState || "No scoring templates available."
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            // ── Tab 4: Activity ───────────────────────────────────────────
            Item {
                AppWidgets.ActivityFeed {
                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    items: root.activityItems
                    emptyText: root.recentActionsModel.emptyState || "No recent portfolio activity."
                }
            }
        }
    }
}
