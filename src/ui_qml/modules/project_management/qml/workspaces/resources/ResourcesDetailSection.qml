import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
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
    property var resourceAvailabilityModel: ({
        "resourceId": "", "peakLoadPercent": 0, "averageLoadPercent": 0,
        "overloadedDays": 0, "availableDays": 0, "isAvailable": true,
        "fromDateLabel": "", "toDateLabel": "", "days": []
    })

    property bool canManageSkills: true
    property var resourceAssignmentsTableModel: null

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
        if (root._idx === 7) return _sec8.implicitHeight
        if (root._idx === 8) return _sec7.implicitHeight
        return 0
    }

    implicitHeight: _activeSectionH
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 0
        loadingMessage: "Loading overview..."
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Overview" }

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
        loadingMessage: "Loading assignments..."
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Assignments" }

                Item {
                    width: parent.width
                    implicitHeight: Theme.AppTheme.spacingMd
                }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: !root._hasResource
                    title: "No resource selected"
                    message: "Select a resource to view its project and task assignments."
                }

                AppWidgets.DataTable {
                    width: parent.width
                    height: Math.min(480, Math.max(200, implicitHeight))
                    visible: root._hasResource
                    columns: [
                        { key: "title",       label: "Task",        flex: 2,   sortable: true  },
                        { key: "subtitle",    label: "Project",     flex: 2                    },
                        { key: "statusLabel", label: "Allocation",  flex: 0,   minWidth: 100, type: "status" },
                        { key: "metaText",    label: "Hours Logged",flex: 1,   minWidth: 100  }
                    ]
                    sourceModel: root.resourceAssignmentsTableModel
                    loading: root.isBusy
                    emptyText: root._hasResource
                        ? "No task assignments found for this resource."
                        : "Select a resource to view assignments."
                }

                Item {
                    width: parent.width
                    implicitHeight: Theme.AppTheme.spacingMd
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 2
        loadingMessage: "Loading capacity..."
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Capacity" }
                Item {
                    width: parent.width
                    implicitHeight: _capacityCol.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

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
        loadingMessage: "Loading calendar..."
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Calendar" }

                AppWidgets.ContextualActionToolbar {
                    width: parent.width
                    title: root._hasResource ? root.resourceDetail.title : "Calendar"
                    subtitle: root._hasResource ? "Working schedule and availability exceptions" : ""
                    busy: root.isBusy
                    actions: [
                        { id: "set_hours",     label: "Set Working Hours", icon: "time",     enabled: root._hasResource },
                        { id: "add_exception", label: "Add Exception",     icon: "add",      enabled: root._hasResource },
                        { id: "add_leave",     label: "Add Leave",         icon: "calendar", enabled: root._hasResource }
                    ]
                    onActionTriggered: function(actionId) {
                        // Placeholder — calendar management UI to be implemented
                    }
                }

                Item {
                    width: parent.width
                    implicitHeight: Theme.AppTheme.spacingMd
                }

                AppWidgets.InlineMessage {
                    width: parent.width
                    anchors.leftMargin: Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    visible: root._hasResource
                    tone: "info"
                    message: "Work calendar configuration — shift schedules, leave periods, and availability exceptions — will be available in an upcoming release."
                }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: !root._hasResource
                    title: "No resource selected"
                    message: "Select a resource to view and configure its work calendar."
                }

                Item {
                    width: parent.width
                    implicitHeight: Theme.AppTheme.spacingMd
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec4
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 4
        loadingMessage: "Loading skills..."
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
                        createLabel: (root._hasResource && root.canManageSkills) ? "Add Skill" : ""
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
                            sourceModel: root.workspaceController ? root.workspaceController.resourceSkillsTableModel : null
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
        loadingMessage: "Loading certifications..."
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
                        createLabel: (root._hasResource && root.canManageSkills) ? "Add Certification" : ""
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
                            sourceModel: root.workspaceController ? root.workspaceController.resourceCertificationsTableModel : null
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
        loadingMessage: "Loading cost rates..."
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Cost Rates" }
                Item {
                    width: parent.width
                    implicitHeight: _costRatesCol.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

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
        id: _sec8
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 7
        loadingMessage: "Loading availability..."
        sourceComponent: Component {
            Column {
                id: _availSection
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading { width: parent.width; label: "Availability" }

                // ── No resource selected ──────────────────────────────────
                AppWidgets.EmptyState {
                    width: parent.width
                    visible: !root._hasResource
                    title: "No resource selected"
                    message: "Select a resource to review its 90-day capacity outlook."
                }

                // ── Main availability content ─────────────────────────────
                ColumnLayout {
                    width: parent.width
                    spacing: Theme.AppTheme.spacingMd
                    visible: root._hasResource

                    // Spacer
                    Item { Layout.preferredHeight: Theme.AppTheme.spacingSm }

                    // ── Status header ─────────────────────────────────────
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.AppTheme.marginMd
                        Layout.rightMargin: Theme.AppTheme.marginMd
                        implicitHeight: _statusRow.implicitHeight + Theme.AppTheme.spacingMd * 2
                        radius: Theme.AppTheme.radiusMd
                        color: {
                            const over = root.resourceAvailabilityModel.overloadedDays || 0
                            const peak = root.resourceAvailabilityModel.peakLoadPercent || 0
                            if (over > 0) return Theme.AppTheme.dangerSoft
                            if (peak >= 80) return Theme.AppTheme.warningSoft
                            return Theme.AppTheme.successSoft
                        }
                        border.width: 1
                        border.color: {
                            const over = root.resourceAvailabilityModel.overloadedDays || 0
                            const peak = root.resourceAvailabilityModel.peakLoadPercent || 0
                            if (over > 0) return Theme.AppTheme.dangerSoftBorder
                            if (peak >= 80) return Theme.AppTheme.warningSoftBorder
                            return Theme.AppTheme.successSoftBorder
                        }

                        RowLayout {
                            id: _statusRow
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.margins: Theme.AppTheme.spacingMd
                            spacing: Theme.AppTheme.spacingSm

                            AppIcons.AppIcon {
                                name: (root.resourceAvailabilityModel.overloadedDays || 0) > 0 ? "risk" : "approve"
                                size: Theme.AppTheme.iconMd
                                iconColor: (root.resourceAvailabilityModel.overloadedDays || 0) > 0
                                    ? Theme.AppTheme.danger : Theme.AppTheme.success
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                AppControls.Label {
                                    text: (root.resourceAvailabilityModel.overloadedDays || 0) > 0
                                        ? "Capacity conflict detected"
                                        : (root.resourceAvailabilityModel.peakLoadPercent || 0) >= 80
                                            ? "Near capacity threshold"
                                            : "Resource available"
                                    color: (root.resourceAvailabilityModel.overloadedDays || 0) > 0
                                        ? Theme.AppTheme.danger
                                        : (root.resourceAvailabilityModel.peakLoadPercent || 0) >= 80
                                            ? Theme.AppTheme.warning
                                            : Theme.AppTheme.success
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    text: {
                                        const from = root.resourceAvailabilityModel.fromDateLabel || ""
                                        const to   = root.resourceAvailabilityModel.toDateLabel   || ""
                                        return (from && to) ? from + "  –  " + to : "90-day outlook"
                                    }
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                            }
                        }
                    }

                    // ── 4 KPI tiles ───────────────────────────────────────
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.AppTheme.marginMd
                        Layout.rightMargin: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: [
                                {
                                    label: "Peak Load",
                                    value: (root.resourceAvailabilityModel.peakLoadPercent || 0).toFixed(0) + "%",
                                    danger: (root.resourceAvailabilityModel.peakLoadPercent || 0) > 100,
                                    warn:   (root.resourceAvailabilityModel.peakLoadPercent || 0) >= 80,
                                    icon: "dashboard"
                                },
                                {
                                    label: "Avg Load",
                                    value: (root.resourceAvailabilityModel.averageLoadPercent || 0).toFixed(0) + "%",
                                    danger: false,
                                    warn:   false,
                                    icon: "financials"
                                },
                                {
                                    label: "Overloaded Days",
                                    value: String(root.resourceAvailabilityModel.overloadedDays || 0),
                                    danger: (root.resourceAvailabilityModel.overloadedDays || 0) > 0,
                                    warn:   false,
                                    icon: "risk"
                                },
                                {
                                    label: "Available Days",
                                    value: String(root.resourceAvailabilityModel.availableDays || 0),
                                    danger: false,
                                    warn:   false,
                                    icon: "calendar"
                                }
                            ]

                            delegate: Rectangle {
                                id: _kpiTile
                                required property var modelData
                                Layout.fillWidth: true
                                implicitHeight: _kpiCol.implicitHeight + Theme.AppTheme.spacingMd * 2
                                radius: Theme.AppTheme.radiusMd
                                color: Theme.AppTheme.surfaceOverlay
                                border.color: Theme.AppTheme.subtleBorder
                                border.width: 1

                                ColumnLayout {
                                    id: _kpiCol
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.margins: Theme.AppTheme.spacingSm
                                    spacing: 3

                                    AppIcons.AppIcon {
                                        name: _kpiTile.modelData.icon
                                        size: Theme.AppTheme.iconSm
                                        iconColor: _kpiTile.modelData.danger
                                            ? Theme.AppTheme.danger
                                            : _kpiTile.modelData.warn
                                                ? Theme.AppTheme.warning
                                                : Theme.AppTheme.textMuted
                                    }

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: _kpiTile.modelData.value
                                        color: _kpiTile.modelData.danger
                                            ? Theme.AppTheme.danger
                                            : _kpiTile.modelData.warn
                                                ? Theme.AppTheme.warning
                                                : Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.subtitleSize
                                        font.bold: true
                                    }

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: _kpiTile.modelData.label
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }
                        }
                    }

                    // ── Peak load bar ─────────────────────────────────────
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.AppTheme.marginMd
                        Layout.rightMargin: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingXs

                        RowLayout {
                            Layout.fillWidth: true

                            AppControls.Label {
                                text: "Peak utilisation"
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                            }

                            Item { Layout.fillWidth: true }

                            AppControls.Label {
                                text: (root.resourceAvailabilityModel.peakLoadPercent || 0).toFixed(0) + "% of 100% capacity"
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 8
                            radius: 4
                            color: Theme.AppTheme.surfaceAlt

                            Rectangle {
                                width: Math.min(parent.width, parent.width * Math.min((root.resourceAvailabilityModel.peakLoadPercent || 0) / 100.0, 1.5))
                                height: parent.height
                                radius: parent.radius
                                color: (root.resourceAvailabilityModel.peakLoadPercent || 0) > 100
                                    ? Theme.AppTheme.danger
                                    : (root.resourceAvailabilityModel.peakLoadPercent || 0) >= 80
                                        ? Theme.AppTheme.warning
                                        : Theme.AppTheme.success

                                Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
                            }

                            // 100% marker
                            Rectangle {
                                x: parent.width - 1
                                width: 2
                                height: parent.height + 4
                                y: -2
                                radius: 1
                                color: Theme.AppTheme.borderStrong
                            }
                        }
                    }

                    // ── Daily load timeline chart ─────────────────────────
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.AppTheme.marginMd
                        Layout.rightMargin: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingXs
                        visible: (root.resourceAvailabilityModel.days || []).length > 0

                        AppControls.Label {
                            text: "Daily load — 90-day outlook"
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }

                        // Mini bar chart
                        Item {
                            Layout.fillWidth: true
                            height: 56

                            Row {
                                anchors.fill: parent
                                spacing: 1

                                Repeater {
                                    model: root.resourceAvailabilityModel.days || []
                                    delegate: Item {
                                        id: _barItem
                                        required property var modelData
                                        width: Math.max(2, (parent.width - ((root.resourceAvailabilityModel.days || []).length - 1)) /
                                               Math.max(1, (root.resourceAvailabilityModel.days || []).length))
                                        height: parent.height

                                        readonly property real _pct: Math.min(parseFloat(_barItem.modelData.allocationPercent || 0) / 100.0, 1.5)
                                        readonly property real _barH: Math.max(2, Math.round(_barItem._pct * (parent.height - 4)))
                                        readonly property color _barColor: _barItem.modelData.overloaded
                                            ? Theme.AppTheme.danger
                                            : parseFloat(_barItem.modelData.allocationPercent || 0) >= 80
                                                ? Theme.AppTheme.warning
                                                : parseFloat(_barItem.modelData.allocationPercent || 0) > 0
                                                    ? Theme.AppTheme.success
                                                    : Theme.AppTheme.surfaceAlt

                                        Rectangle {
                                            anchors.bottom: parent.bottom
                                            anchors.bottomMargin: 2
                                            width: parent.width
                                            height: _barItem._barH
                                            radius: 1
                                            color: _barItem._barColor
                                            opacity: 0.85

                                            ToolTip.visible: _barTip.containsMouse
                                            ToolTip.text: String(_barItem.modelData.dateLabel || "") + ": " + String(_barItem.modelData.allocationLabel || "0%")
                                            ToolTip.delay: 400

                                            MouseArea {
                                                id: _barTip
                                                anchors.fill: parent
                                                hoverEnabled: true
                                            }
                                        }
                                    }
                                }
                            }

                            // Capacity line — sits at the top of where a 100% bar would reach
                            Rectangle {
                                anchors.top: parent.top
                                anchors.topMargin: 2
                                width: parent.width
                                height: 1
                                color: Theme.AppTheme.borderStrong
                                opacity: 0.5
                            }
                        }

                        // Legend
                        Row {
                            spacing: Theme.AppTheme.spacingMd

                            Repeater {
                                model: [
                                    { color: Theme.AppTheme.success, label: "Available" },
                                    { color: Theme.AppTheme.warning, label: "Near limit" },
                                    { color: Theme.AppTheme.danger,  label: "Overloaded" }
                                ]
                                delegate: Row {
                                    id: _legendRow
                                    required property var modelData
                                    spacing: Theme.AppTheme.spacingXs
                                    Rectangle {
                                        width: 10; height: 10
                                        radius: 2
                                        color: _legendRow.modelData.color
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    AppControls.Label {
                                        text: _legendRow.modelData.label
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                            }
                        }
                    }

                    // ── No assignment message (chart empty) ───────────────
                    AppWidgets.InlineMessage {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.AppTheme.marginMd
                        Layout.rightMargin: Theme.AppTheme.marginMd
                        visible: (root.resourceAvailabilityModel.days || []).length === 0
                            && root._hasResource
                        tone: "info"
                        message: "No active task assignments in the 90-day window. This resource is fully available."
                    }

                    Item { Layout.preferredHeight: Theme.AppTheme.spacingMd }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec7
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 8
        loadingMessage: "Loading activity..."
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0
                AppWidgets.SectionHeading { width: parent.width; label: "Activity" }
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
