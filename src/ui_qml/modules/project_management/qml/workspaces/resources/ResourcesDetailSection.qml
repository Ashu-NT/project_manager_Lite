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
    property var workspaceController: null

    signal editRequested()
    signal toggleRequested()
    signal deleteRequested()
    signal addSkillRequested()
    signal addCertificationRequested()
    signal removeSkillRequested(string skillId)
    signal removeCertificationRequested(string certId)

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
            Item {
                id: _skillsSection
                width: parent ? parent.width : 0
                implicitHeight: _skillsCol.implicitHeight

                readonly property var _skills: root.workspaceController
                    ? (root.workspaceController.resourceSkills || []) : []
                property string _selectedSkillId: ""
                readonly property var _selectedSkill: {
                    const sid = _skillsSection._selectedSkillId
                    if (!sid) return null
                    const list = _skillsSection._skills
                    for (let i = 0; i < list.length; i++) {
                        if (String(list[i].id || "") === sid) return list[i]
                    }
                    return null
                }
                readonly property int _tableH: {
                    const n = _skillsSection._skills.length
                    const rH = Theme.AppTheme.compactRowHeight
                    const hH = Theme.AppTheme.normalRowHeight
                    return n === 0 ? (hH + 80) : Math.min(hH + n * rH + 12, 300)
                }
                readonly property var _columns: [
                    { key: "title",       label: "Skill",       flex: 2,   sortable: false },
                    { key: "subtitle",    label: "Code",        flex: 1,   sortable: false },
                    { key: "statusLabel", label: "Proficiency", flex: 0,   minWidth: 110, type: "status" },
                    { key: "metaText",    label: "Notes",       flex: 2,   sortable: false }
                ]

                ColumnLayout {
                    id: _skillsCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    spacing: 0

                    AppWidgets.ContextualActionToolbar {
                        Layout.fillWidth: true
                        visible: !_skillsSection._selectedSkillId
                        title: "Skills"
                        subtitle: _skillsSection._skills.length > 0 ? String(_skillsSection._skills.length) : ""
                        busy: root.isBusy
                        createLabel: root._hasResource ? "Add Skill" : ""
                        actions: []
                        onCreateRequested: root.addSkillRequested()
                    }

                    AppWidgets.ContextualActionToolbar {
                        Layout.fillWidth: true
                        visible: Boolean(_skillsSection._selectedSkillId)
                        showBack: true
                        title: _skillsSection._selectedSkill ? String(_skillsSection._selectedSkill.title || "Skill") : "Skill"
                        subtitle: _skillsSection._selectedSkill ? String(_skillsSection._selectedSkill.statusLabel || "") : ""
                        busy: root.isBusy
                        actions: [
                            { id: "remove", label: "Remove", icon: "delete", enabled: true, danger: true }
                        ]
                        onBackRequested: _skillsSection._selectedSkillId = ""
                        onActionTriggered: function(actionId) {
                            if (actionId === "remove" && _skillsSection._selectedSkill)
                                root.removeSkillRequested(String(_skillsSection._selectedSkill.id || ""))
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        implicitHeight: _skillsSection._tableH

                        AppWidgets.DataTable {
                            anchors.fill: parent
                            columns: _skillsSection._columns
                            rows: _skillsSection._skills
                            selectedRowId: _skillsSection._selectedSkillId
                            loading: root.isBusy
                            emptyText: root._hasResource
                                ? "No skills recorded for this resource."
                                : "Select a resource to view its skills."
                            onRowSelected: function(rowId) { _skillsSection._selectedSkillId = rowId }
                            onRowActivated: function(rowId) { _skillsSection._selectedSkillId = rowId }
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
        active: root._idx === 5
        sourceComponent: Component {
            Item {
                id: _certsSection
                width: parent ? parent.width : 0
                implicitHeight: _certsCol.implicitHeight

                readonly property var _certs: root.workspaceController
                    ? (root.workspaceController.resourceCertifications || []) : []
                property string _selectedCertId: ""
                readonly property var _selectedCert: {
                    const cid = _certsSection._selectedCertId
                    if (!cid) return null
                    const list = _certsSection._certs
                    for (let i = 0; i < list.length; i++) {
                        if (String(list[i].id || "") === cid) return list[i]
                    }
                    return null
                }
                readonly property int _tableH: {
                    const n = _certsSection._certs.length
                    const rH = Theme.AppTheme.compactRowHeight
                    const hH = Theme.AppTheme.normalRowHeight
                    return n === 0 ? (hH + 80) : Math.min(hH + n * rH + 12, 300)
                }
                readonly property var _columns: [
                    { key: "title",       label: "Certification", flex: 2,   sortable: false },
                    { key: "subtitle",    label: "Code",          flex: 1,   sortable: false },
                    { key: "statusLabel", label: "Status",        flex: 0,   minWidth: 110, type: "status" },
                    { key: "metaText",    label: "Expiry",        flex: 1,   sortable: false }
                ]

                ColumnLayout {
                    id: _certsCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    spacing: 0

                    AppWidgets.ContextualActionToolbar {
                        Layout.fillWidth: true
                        visible: !_certsSection._selectedCertId
                        title: "Certifications"
                        subtitle: _certsSection._certs.length > 0 ? String(_certsSection._certs.length) : ""
                        busy: root.isBusy
                        createLabel: root._hasResource ? "Add Certification" : ""
                        actions: []
                        onCreateRequested: root.addCertificationRequested()
                    }

                    AppWidgets.ContextualActionToolbar {
                        Layout.fillWidth: true
                        visible: Boolean(_certsSection._selectedCertId)
                        showBack: true
                        title: _certsSection._selectedCert ? String(_certsSection._selectedCert.title || "Certification") : "Certification"
                        subtitle: _certsSection._selectedCert ? String(_certsSection._selectedCert.statusLabel || "") : ""
                        busy: root.isBusy
                        actions: [
                            { id: "remove", label: "Remove", icon: "delete", enabled: true, danger: true }
                        ]
                        onBackRequested: _certsSection._selectedCertId = ""
                        onActionTriggered: function(actionId) {
                            if (actionId === "remove" && _certsSection._selectedCert)
                                root.removeCertificationRequested(String(_certsSection._selectedCert.id || ""))
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        implicitHeight: _certsSection._tableH

                        AppWidgets.DataTable {
                            anchors.fill: parent
                            columns: _certsSection._columns
                            rows: _certsSection._certs
                            selectedRowId: _certsSection._selectedCertId
                            loading: root.isBusy
                            emptyText: root._hasResource
                                ? "No certifications recorded for this resource."
                                : "Select a resource to view its certifications."
                            onRowSelected: function(rowId) { _certsSection._selectedCertId = rowId }
                            onRowActivated: function(rowId) { _certsSection._selectedCertId = rowId }
                        }
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
