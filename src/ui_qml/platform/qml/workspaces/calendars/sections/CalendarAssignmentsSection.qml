pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Answers "where is this calendar currently used?" -- a calendar-centric
// administration/impact-assessment view, grouped by consuming entity type.
// This is NOT the same question as "which calendar does Site/Department/
// Employee X inherit?" (that's the target entity's own Calendar section).
// Projects/Resources show only their id: Platform has no approved cross-
// module contract to resolve PM display names (see serialize_assignment_groups).
Item {
    id: root

    property var assignments: ({
        "sites": [], "departments": [], "employees": [], "projects": [], "resources": []
    })
    property bool isOrganizationDefault: false
    property bool busy: false

    signal refreshRequested()

    readonly property var _groups: [
        { "key": "sites", "title": "Sites", "rows": root.assignments.sites || [] },
        { "key": "departments", "title": "Departments", "rows": root.assignments.departments || [] },
        { "key": "employees", "title": "Employees", "rows": root.assignments.employees || [] },
        { "key": "projects", "title": "Projects", "rows": root.assignments.projects || [] },
        { "key": "resources", "title": "Resources", "rows": root.assignments.resources || [] }
    ]
    readonly property int _totalAssignments: root._groups.reduce(function(sum, g) { return sum + g.rows.length }, 0)

    function _rowLabel(row) {
        const name = String(row.entityName || "").trim()
        return name.length > 0 ? name : String(row.entityId || "")
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            showSearch: false
            showRefresh: true
            showCreate: false
            showImport: false
            showExport: false
            showFilter: false
            showCustomize: false
            showViews: false
            isBusy: root.busy
            onRefreshRequested: root.refreshRequested()
        }

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: width
            contentHeight: assignmentsColumn.implicitHeight
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: assignmentsColumn
                width: Math.min(parent.width, 760)
                anchors.left: parent.left
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.SectionCard {
                    Layout.fillWidth: true
                    title: "Organization"
                    outlined: true

                    RowLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label {
                            text: root.isOrganizationDefault
                                ? "This is the organization's default calendar."
                                : "This is not the organization's default calendar."
                            color: Theme.AppTheme.textPrimary
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            Layout.fillWidth: true
                        }

                        AppWidgets.StatusChip {
                            visible: root.isOrganizationDefault
                            status: "Organization Default"
                            tone: "info"
                        }
                    }
                }

                Repeater {
                    model: root._groups

                    delegate: AppWidgets.SectionCard {
                        required property var modelData
                        Layout.fillWidth: true
                        visible: modelData.rows.length > 0
                        title: modelData.title + " (" + modelData.rows.length + ")"
                        outlined: true

                        ColumnLayout {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: Theme.AppTheme.marginMd
                            spacing: Theme.AppTheme.spacingXs

                            Repeater {
                                model: modelData.rows

                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingSm

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: root._rowLabel(modelData)
                                        color: Theme.AppTheme.textPrimary
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                    }

                                    AppControls.Label {
                                        visible: String(modelData.effectiveFrom || "").length > 0 || String(modelData.effectiveTo || "").length > 0
                                        text: String(modelData.effectiveFrom || "-") + " → " + String(modelData.effectiveTo || "-")
                                        color: Theme.AppTheme.textMuted
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                }
                            }
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root._totalAssignments === 0
                    tone: "info"
                    message: "No sites, departments, employees, projects, or resources are directly assigned to this calendar."
                }
            }
        }
    }
}
