import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property var projectDetail: ({
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "emptyState": "",
        "fields": [],
        "state": {}
    })
    property bool isBusy: false
    property var detailPage: null
    property var sectionErrors: ({})
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog

    signal editRequested()
    signal statusRequested()
    signal deleteRequested()

    function _sv(key) {
        const s = root.projectDetail.state || {}
        return String(s[key] || "")
    }

    readonly property bool _hasProject: String(root.projectDetail.id || "").length > 0
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property var _sections: root.detailPage ? (root.detailPage.sections || []) : []

    function _secIdx(name) { return root._sections.indexOf(name) }

    readonly property int _activeSectionH: {
        const name = root._sections[root._idx] || ""
        if (name === "Overview")        return _sec0.implicitHeight
        if (name === "Schedule")        return _sec1.implicitHeight
        if (name === "Tasks")           return _sec2.implicitHeight
        if (name === "Resources")       return _sec3.implicitHeight
        if (name === "Financials")      return _sec4.implicitHeight
        if (name === "Risks")           return _sec5.implicitHeight
        if (name === "Documents")       return _sec6.implicitHeight
        if (name === "Activity")        return _sec7.implicitHeight
        if (name === "Material Demand") return _sec8.implicitHeight
        if (name === "Procurement")     return _sec9.implicitHeight
        return 0
    }

    implicitHeight: _activeSectionH
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Overview")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Overview"
                }

                Item {
                    width: parent.width
                    implicitHeight: _overviewCol.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ColumnLayout {
                        id: _overviewCol
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: !root._hasProject
                            title: "No project selected"
                            message: root.projectDetail.emptyState
                                || "Select a project from the catalog to review details or edit its setup."
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: root._hasProject
                            spacing: Theme.AppTheme.spacingMd

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label {
                                    text: "Client"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("clientName") || "-"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    elide: Text.ElideRight
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label {
                                    text: "Contact"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("clientContact") || "-"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    elide: Text.ElideRight
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label {
                                    text: "Start"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("startDateLabel") || "-"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label {
                                    text: "Finish"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("endDateLabel") || "-"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            visible: root._hasProject
                            color: Theme.AppTheme.divider
                            opacity: 0.5
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: root._hasProject
                            spacing: Theme.AppTheme.spacingMd

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label {
                                    text: "Budget"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("plannedBudgetLabel") || "-"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label {
                                    text: "Currency"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("currency") || "-"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label {
                                    text: "Status"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppWidgets.StatusChip {
                                    status: root.projectDetail.statusLabel || ""
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label {
                                    text: "Version"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("version") ? "v" + root._sv("version") : "-"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: root._hasProject
                            text: root.projectDetail.description
                                || "No project description has been added yet."
                            color: String(root.projectDetail.description || "").length > 0
                                ? Theme.AppTheme.textSecondary
                                : Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                            maximumLineCount: 4
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec1
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Schedule")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Schedule"
                }

                Item {
                    width: parent.width
                    implicitHeight: _scheduleContent.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ColumnLayout {
                        id: _scheduleContent
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingXs

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: !root._hasProject
                            title: "No schedule data"
                            message: "Select a project to review its schedule."
                        }

                        Item {
                            Layout.fillWidth: true
                            visible: root._hasProject
                            implicitHeight: _scheduleGrid.implicitHeight

                            GridLayout {
                                id: _scheduleGrid
                                width: parent.width
                                columns: 2
                                columnSpacing: Theme.AppTheme.spacingMd
                                rowSpacing: Theme.AppTheme.spacingXs

                                AppControls.Label {
                                    text: "Start Date"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("startDateLabel") || "Not scheduled"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }

                                AppControls.Label {
                                    text: "Finish Date"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("endDateLabel") || "Not scheduled"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Tasks")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Tasks" }

                AppWidgets.InlineMessage {
                    width: parent.width
                    visible: String(root.sectionErrors["tasks"] || "").length > 0
                    tone: "danger"
                    message: String(root.sectionErrors["tasks"] || "")
                }

                Item {
                    width: parent.width
                    implicitHeight: _tasksEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    AppWidgets.EmptyState {
                        id: _tasksEmpty
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                        title: "Task execution data"
                        message: "Open the Tasks workspace to view delivery tasks assigned to this project."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec3
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Resources")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Resources" }

                AppWidgets.InlineMessage {
                    width: parent.width
                    visible: String(root.sectionErrors["resources"] || "").length > 0
                    tone: "danger"
                    message: String(root.sectionErrors["resources"] || "")
                }

                Item {
                    width: parent.width
                    implicitHeight: _resourcesEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    AppWidgets.EmptyState {
                        id: _resourcesEmpty
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                        title: "Resource allocation data"
                        message: "Open the Resources workspace to review staffing and capacity assigned to this project."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec4
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Financials")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Financials"
                }

                AppWidgets.InlineMessage {
                    width: parent.width
                    visible: String(root.sectionErrors["financials"] || "").length > 0
                    tone: "danger"
                    message: String(root.sectionErrors["financials"] || "")
                }

                Item {
                    width: parent.width
                    implicitHeight: _financialsCol.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ColumnLayout {
                        id: _financialsCol
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: !root._hasProject
                            title: "No financial data"
                            message: "Select a project to review its financial information."
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: root._hasProject
                            spacing: Theme.AppTheme.spacingMd

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label {
                                    text: "Planned Budget"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("plannedBudgetLabel") || "-"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label {
                                    text: "Currency"
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: root._sv("currency") || "-"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }

                            Item { Layout.fillWidth: true }
                            Item { Layout.fillWidth: true }
                        }

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: root._hasProject
                            title: "Cost tracking data"
                            message: "Open the Financials workspace to review actuals, commitments, and forecast against this project's budget."
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec5
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Risks")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Risks" }

                AppWidgets.InlineMessage {
                    width: parent.width
                    visible: String(root.sectionErrors["risks"] || "").length > 0
                    tone: "danger"
                    message: String(root.sectionErrors["risks"] || "")
                }

                Item {
                    width: parent.width
                    implicitHeight: _risksEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    AppWidgets.EmptyState {
                        id: _risksEmpty
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                        title: "Risk register"
                        message: "Open the Register workspace to view risks, issues, and change requests tracked against this project."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec6
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Documents")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Documents" }

                AppWidgets.InlineMessage {
                    width: parent.width
                    visible: String(root.sectionErrors["documents"] || "").length > 0
                    tone: "danger"
                    message: String(root.sectionErrors["documents"] || "")
                }

                Item {
                    width: parent.width
                    implicitHeight: _documentsEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    AppWidgets.EmptyState {
                        id: _documentsEmpty
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                        title: "Project documents"
                        message: "Document management is not yet configured for this project."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec7
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Activity")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Activity" }

                AppWidgets.InlineMessage {
                    width: parent.width
                    visible: String(root.sectionErrors["activity"] || "").length > 0
                    tone: "danger"
                    message: String(root.sectionErrors["activity"] || "")
                }

                Item {
                    width: parent.width
                    implicitHeight: Math.max(_activityFeed.implicitHeight, 80) + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    AppWidgets.ActivityFeed {
                        id: _activityFeed
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd
                        items: {
                            const s = root.projectDetail.state || {}
                            return s.activityItems || []
                        }
                        emptyText: "No project activity recorded"
                    }
                }
            }
        }
    }

    // ── Material Demand (capability-gated: inventory.reservations.create) ──
    AppWidgets.LazySectionLoader {
        id: _sec8
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Material Demand")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Material Demand" }

                Item {
                    width: parent.width
                    implicitHeight: _matDemandContent.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ColumnLayout {
                        id: _matDemandContent
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: !root._hasProject
                            title: "No project selected"
                            message: "Select a project to view material demand and reservations."
                        }

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: root._hasProject
                            title: "Material demand tracking"
                            message: "Open the Tasks workspace and select a task to create or manage inventory reservations for this project."
                        }
                    }
                }
            }
        }
    }

    // ── Procurement (capability-gated: procurement.purchase_orders.read) ──
    AppWidgets.LazySectionLoader {
        id: _sec9
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Procurement")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Procurement" }

                Item {
                    width: parent.width
                    implicitHeight: _procContent.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ColumnLayout {
                        id: _procContent
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: !root._hasProject
                            title: "No project selected"
                            message: "Select a project to view procurement commitments."
                        }

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: root._hasProject
                            title: "Procurement commitments"
                            message: "Open the Financials workspace to review purchase requisitions and committed procurement costs linked to this project."
                        }
                    }
                }
            }
        }
    }
}
