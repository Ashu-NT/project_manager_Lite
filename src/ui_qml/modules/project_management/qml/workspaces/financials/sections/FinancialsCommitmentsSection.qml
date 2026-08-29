pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var commitmentSummaryModel: ({
        "approvedBudgetLabel": "", "postedActualLabel": "",
        "openCommitmentLabel": "", "availableAfterCommitmentLabel": "",
        "commitmentRatePct": 0
    })
    property var commitmentsModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var commitmentsTableModel: null
    property bool isBusy: false
    property string sortKey: "metaText"
    property int sortDirection: Qt.DescendingOrder

    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)
    signal sortRequested(string key, int direction)

    readonly property var _columns: [
        { "key": "title", "label": "Source line", "flex": 1.5, "sortable": true },
        { "key": "subtitle", "label": "Lifecycle", "flex": 1, "sortable": false },
        { "key": "statusLabel", "label": "Committed", "flex": 0, "minWidth": 120, "sortable": true },
        { "key": "supportingText", "label": "Matched / Remaining", "flex": 2, "sortable": false },
        { "key": "metaText", "label": "Delivery / Order", "flex": 0, "minWidth": 130, "sortable": true }
    ]

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Commitments" }

        Item {
            width: parent.width
            implicitHeight: _commitContent.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _commitContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 0

                    Repeater {
                        model: [
                            { "lbl": "Approved budget", "val": root.commitmentSummaryModel.approvedBudgetLabel || "-" },
                            { "lbl": "Posted actual", "val": root.commitmentSummaryModel.postedActualLabel || "-" },
                            { "lbl": "Open commitment", "val": root.commitmentSummaryModel.openCommitmentLabel || "-" },
                            { "lbl": "Available", "val": root.commitmentSummaryModel.availableAfterCommitmentLabel || "-" }
                        ]

                        delegate: ColumnLayout {
                            id: _commitCell
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_commitCell.modelData.lbl)
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_commitCell.modelData.val)
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                                wrapMode: Text.NoWrap
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 0

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs
                        AppControls.Label { Layout.fillWidth: true; text: "Open commitment"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize }
                        AppControls.Label { Layout.fillWidth: true; text: String(root.commitmentSummaryModel.openCommitmentLabel || "-"); color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.bodySize; font.bold: true }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs
                        AppControls.Label { Layout.fillWidth: true; text: "Commitment Rate"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize }
                        AppControls.Label { Layout.fillWidth: true; text: Number(root.commitmentSummaryModel.commitmentRatePct || 0).toFixed(1) + "%"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.bodySize; font.bold: true }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs
                        AppControls.Label { Layout.fillWidth: true; text: "Available after actual + commitment"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize }
                        AppControls.Label { Layout.fillWidth: true; text: String(root.commitmentSummaryModel.availableAfterCommitmentLabel || "-"); color: Theme.AppTheme.textSecondary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: String(root.commitmentSummaryModel.approvedBudgetLabel || "").length === 0
                    text: "Select a project to view the commitment lifecycle breakdown."
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: root.commitmentsModel.subtitle || "Procurement commitment lifecycle"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: (root.commitmentsModel.items || []).length === 0
                    title: root.commitmentsModel.emptyState || "No commitments"
                    message: "No procurement commitment lines are linked to this project."
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 240
                    visible: (root.commitmentsModel.items || []).length > 0

                    AppWidgets.DataTable {
                        anchors.fill: parent
                        columns: root._columns
                        sourceModel: root.commitmentsTableModel
                        sortingMode: "server"
                        sortKey: root.sortKey
                        sortDirection: root.sortDirection
                        loading: root.isBusy
                        emptyText: root.commitmentsModel.emptyState || "No commitments."
                        onSortRequested: function(key, direction) {
                            root.sortRequested(key, direction)
                        }
                    }
                }

                AppWidgets.TablePaginationBar {
                    Layout.fillWidth: true
                    visible: Number(root.commitmentsModel.total || 0) > Number(root.commitmentsModel.pageSize || 50)
                    currentPage: Number(root.commitmentsModel.page || 1)
                    pageSize: Number(root.commitmentsModel.pageSize || 50)
                    totalItems: Number(root.commitmentsModel.total || 0)
                    busy: root.isBusy
                    onPageRequested: function(page) { root.pageRequested(page) }
                    onPageSizeRequested: function(pageSize) { root.pageSizeRequested(pageSize) }
                }
            }
        }
    }
}
