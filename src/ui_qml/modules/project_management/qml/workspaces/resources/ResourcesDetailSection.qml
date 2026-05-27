import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var resourceDetail: ({
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "emptyState": "Select a resource from the pool to review details or edit its setup.",
        "fields": [],
        "state": {}
    })
    property bool isBusy: false
    property var detailPage: null

    signal editRequested()
    signal toggleRequested()
    signal deleteRequested()

    function _sv(key) {
        const s = root.resourceDetail.state || {}
        return String(s[key] || "")
    }

    readonly property bool _hasResource: String(root.resourceDetail.id || "").length > 0
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property int _activeSectionH: {
        if (root._idx === 0) return _sec0.implicitHeight
        if (root._idx === 1) return _sec1.implicitHeight
        if (root._idx === 2) return _sec2.implicitHeight
        if (root._idx === 3) return _sec3.implicitHeight
        if (root._idx === 4) return _sec4.implicitHeight
        if (root._idx === 5) return _sec5.implicitHeight
        if (root._idx === 6) return _sec6.implicitHeight
        return _sec7.implicitHeight
    }

    implicitHeight: _activeSectionH

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 0
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Overview" }

                Item {
                    width: parent.width
                    implicitHeight: _overviewCol.implicitHeight + Theme.AppTheme.spacingMd * 2

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
                            visible: !root._hasResource
                            title: "No resource selected"
                            message: root.resourceDetail.emptyState
                                || "Select a resource from the pool to review details or edit its setup."
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: root._hasResource
                            spacing: Theme.AppTheme.spacingMd

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label { text: "Role"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label { Layout.fillWidth: true; text: root._sv("role") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; elide: Text.ElideRight }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label { text: "Type"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label { Layout.fillWidth: true; text: root._sv("workerTypeLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label { text: "Capacity"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: {
                                        const pct = parseFloat(root._sv("capacityPercent") || "0")
                                        return root._sv("capacityLabel") || (pct.toFixed(0) + "%")
                                    }
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label { text: "Rate"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label { Layout.fillWidth: true; text: root._sv("hourlyRateLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            visible: root._hasResource
                            color: Theme.AppTheme.divider
                            opacity: 0.5
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: root._hasResource
                            spacing: Theme.AppTheme.spacingMd

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label { text: "Contact"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label { Layout.fillWidth: true; text: root._sv("contact") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; elide: Text.ElideRight }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label { text: "Currency"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label { Layout.fillWidth: true; text: root._sv("currency") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label { text: "Status"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppWidgets.StatusChip { status: root.resourceDetail.statusLabel || "" }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                AppControls.Label { text: "Version"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label { Layout.fillWidth: true; text: root._sv("version") ? "v" + root._sv("version") : "-"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize }
                            }
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: root._hasResource
                            text: root.resourceDetail.description || "No additional details have been added for this resource."
                            color: String(root.resourceDetail.description || "").length > 0
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
        active: root._idx === 1
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Assignments" }
                Item {
                    width: parent.width
                    implicitHeight: _assignmentsEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2
                    AppWidgets.EmptyState {
                        id: _assignmentsEmpty
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                        title: "Project assignments"
                        message: "Open the Tasks workspace to view project and task assignments for this resource."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 2
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Capacity" }
                Item {
                    width: parent.width
                    implicitHeight: _capacityCol.implicitHeight + Theme.AppTheme.spacingMd * 2

                    ColumnLayout {
                        id: _capacityCol
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: !root._hasResource
                            title: "No capacity data"
                            message: "Select a resource to review its capacity settings."
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 52
                            visible: root._hasResource

                            Rectangle {
                                anchors.fill: parent
                                radius: Theme.AppTheme.radiusMd
                                color: Theme.AppTheme.surfaceAlt

                                readonly property real _pct: {
                                    const s = root.resourceDetail.state || {}
                                    return Math.min(parseFloat(s.capacityPercent || "0"), 100.0) / 100.0
                                }
                                readonly property string _label: {
                                    const s = root.resourceDetail.state || {}
                                    const pct = parseFloat(s.capacityPercent || "0")
                                    return s.capacityLabel || (pct.toFixed(0) + "%")
                                }

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: Theme.AppTheme.spacingMd
                                    spacing: Theme.AppTheme.spacingXs

                                    RowLayout {
                                        Layout.fillWidth: true
                                        AppControls.Label { text: "Capacity"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                        Item { Layout.fillWidth: true }
                                        AppControls.Label { text: parent.parent.parent._label; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                    }

                                    AppWidgets.ProgressBar {
                                        Layout.fillWidth: true
                                        value: parent.parent._pct
                                        Layout.preferredHeight: 6
                                    }
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            visible: root._hasResource && String((root.resourceDetail.state || {}).hourlyRateLabel || "").length > 0

                            Rectangle {
                                anchors.fill: parent
                                radius: Theme.AppTheme.radiusMd
                                color: Theme.AppTheme.surfaceAlt

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.AppTheme.spacingMd
                                    anchors.rightMargin: Theme.AppTheme.spacingMd
                                    spacing: Theme.AppTheme.spacingSm

                                    AppControls.Label { text: "Hourly Rate"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                                    Item { Layout.fillWidth: true }
                                    AppControls.Label { text: root._sv("hourlyRateLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.bodySize; font.bold: true }
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            visible: root._hasResource
                            Rectangle {
                                anchors.fill: parent
                                radius: Theme.AppTheme.radiusMd
                                color: Theme.AppTheme.surfaceAlt
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.AppTheme.spacingMd
                                    anchors.rightMargin: Theme.AppTheme.spacingMd
                                    spacing: Theme.AppTheme.spacingSm
                                    AppControls.Label { text: "Cost Type"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                                    Item { Layout.fillWidth: true }
                                    AppControls.Label { text: root._sv("costTypeLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec3
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 3
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Calendar" }
                Item {
                    width: parent.width
                    implicitHeight: _calendarEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2
                    AppWidgets.EmptyState {
                        id: _calendarEmpty
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                        title: "Work calendar"
                        message: "Shift schedules, availability exceptions, and leave periods are not yet configured for this resource."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec4
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 4
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Skills" }
                Item {
                    width: parent.width
                    implicitHeight: _skillsEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2
                    AppWidgets.EmptyState {
                        id: _skillsEmpty
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                        title: "Skills and competencies"
                        message: "Skill profiles and competency levels have not been configured for this resource."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec5
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 5
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Certifications" }
                Item {
                    width: parent.width
                    implicitHeight: _certificationsEmpty.implicitHeight + Theme.AppTheme.spacingMd * 2
                    AppWidgets.EmptyState {
                        id: _certificationsEmpty
                        anchors.top: parent.top
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: Math.min(parent.width - Theme.AppTheme.marginMd * 2, 400)
                        title: "Certifications"
                        message: "No certifications or compliance records have been linked to this resource."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec6
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 6
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Cost Rates" }
                Item {
                    width: parent.width
                    implicitHeight: _costRatesCol.implicitHeight + Theme.AppTheme.spacingMd * 2

                    ColumnLayout {
                        id: _costRatesCol
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        AppWidgets.EmptyState {
                            Layout.fillWidth: true
                            visible: !root._hasResource
                            title: "No cost rate data"
                            message: "Select a resource to review its cost rate configuration."
                        }

                        Item {
                            Layout.fillWidth: true
                            visible: root._hasResource
                            implicitHeight: _costRatesGrid.implicitHeight

                            GridLayout {
                                id: _costRatesGrid
                                width: parent.width
                                columns: 2
                                columnSpacing: Theme.AppTheme.spacingMd
                                rowSpacing: Theme.AppTheme.spacingXs

                                AppControls.Label { text: "Hourly Rate"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label { Layout.fillWidth: true; text: root._sv("hourlyRateLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                                AppControls.Label { text: "Currency"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label { Layout.fillWidth: true; text: root._sv("currency") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                                AppControls.Label { text: "Cost Type"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label { Layout.fillWidth: true; text: root._sv("costTypeLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                                AppControls.Label { text: "Worker Type"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                                AppControls.Label { Layout.fillWidth: true; text: root._sv("workerTypeLabel") || "-"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                            }
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec7
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 7
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Activity" }
                Item {
                    width: parent.width
                    implicitHeight: Math.max(_activityFeed.implicitHeight, 80) + Theme.AppTheme.spacingMd * 2
                    AppWidgets.ActivityFeed {
                        id: _activityFeed
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd
                        items: {
                            const s = root.resourceDetail.state || {}
                            return s.activityItems || []
                        }
                        emptyText: "No resource activity recorded"
                    }
                }
            }
        }
    }
}
