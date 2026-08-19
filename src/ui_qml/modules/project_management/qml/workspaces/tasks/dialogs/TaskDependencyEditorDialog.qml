pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// one shared dialog for both Create and Edit. Create picks the
// direction, related task, relationship type and lag/lead; Edit only ever
// touches relationship type and lag/lead (the two endpoints of an existing
// dependency can't be changed -- remove and re-add instead). Both modes
// surface a relationship preview (N8) and a live, non-persisting schedule
// impact preview from the typed backend (N9) -- this dialog never computes
// any schedule math itself.
AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property var taskData: ({})
    property var dependencyData: ({})
    property var taskOptions: []
    property var dependencyTypeOptions: []
    property var workspaceController: null
    property var _impactPreview: ({})

    readonly property var relationshipOptions: [
        { "value": "PREDECESSOR", "label": "Current task depends on other task" },
        { "value": "SUCCESSOR",   "label": "Other task depends on current task" }
    ]

    signal submitted(var payload)

    title: root.mode === "create" ? "Add Dependency" : "Edit Relationship"
    subtitle: root.mode === "create"
        ? (root.taskData && root.taskData.title
            ? "Define sequencing around " + root.taskData.title + "."
            : "Define predecessor or successor flow for the selected task.")
        : "Update the relationship type or lag/lead for this dependency."
    primaryText:  root.mode === "create" ? "Add Dependency" : "Save Changes"
    primaryIcon:  root.mode === "create" ? "add" : "save"
    primaryEnabled: root.mode === "edit" || (root.taskOptions || []).length > 0
    width: 560

    function populateForm() {
        root.errorMessage = ""
        root._impactPreview = ({})
        if (root.mode === "edit") {
            const state = root.dependencyState()
            dependencyTypeCombo.currentIndex = root.indexForValue(root.dependencyTypeOptions, state.dependencyType || "FS")
            lagField.text = String(state.lagDays || "0")
        } else {
            linkedTaskCombo.currentIndex = 0
            relationshipCombo.currentIndex = 0
            dependencyTypeCombo.currentIndex = root.indexForValue(root.dependencyTypeOptions, "FS")
            lagField.text = "0"
        }
        Qt.callLater(root.runImpactPreview)
    }

    onOpened: root.populateForm()
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function indexForValue(options, targetValue) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function taskState() {
        return root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
    }

    function dependencyState() {
        return root.dependencyData && root.dependencyData.state
            ? root.dependencyData.state
            : (root.dependencyData || {})
    }

    function selectedDependencyTypeValue() {
        const opt = root.dependencyTypeOptions[dependencyTypeCombo.currentIndex] || {}
        return String(opt.value || "FS")
    }

    function buildPayload() {
        if (root.mode === "edit") {
            const state = root.dependencyState()
            return {
                "dependencyId": String(state.dependencyId || root.dependencyData.id || ""),
                "dependencyType": root.selectedDependencyTypeValue(),
                "lagDays": lagField.text,
                "version": String(state.version || "")
            }
        }
        const taskOption = root.taskOptions[linkedTaskCombo.currentIndex] || {}
        const relationshipOption = root.relationshipOptions[relationshipCombo.currentIndex] || {}
        return {
            "taskId": String(root.taskState().taskId || ""),
            "linkedTaskId": String(taskOption.value || ""),
            "relationshipDirection": String(relationshipOption.value || "PREDECESSOR"),
            "dependencyType": root.selectedDependencyTypeValue(),
            "lagDays": lagField.text
        }
    }

    function submitDialog() {
        if (root.mode === "create"
                && String((root.taskOptions[linkedTaskCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Select a linked task before creating the dependency."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    // ── N9: live, non-persisting schedule impact preview ───────────────
    function runImpactPreview() {
        if (root.workspaceController === null) {
            root._impactPreview = ({})
            return
        }
        const dependenciesController = root.workspaceController.dependenciesController
        if (!dependenciesController) {
            root._impactPreview = ({})
            return
        }
        if (root.mode === "edit") {
            const state = root.dependencyState()
            if (!state.dependencyId) {
                root._impactPreview = ({})
                return
            }
            root._impactPreview = dependenciesController.previewUpdateDependency({
                "dependencyId": String(state.dependencyId || ""),
                "dependencyType": root.selectedDependencyTypeValue(),
                "lagDays": lagField.text
            }) || {}
            return
        }
        const taskOption = root.taskOptions[linkedTaskCombo.currentIndex] || {}
        const linkedTaskId = String(taskOption.value || "")
        const taskId = String(root.taskState().taskId || "")
        if (!linkedTaskId || !taskId) {
            root._impactPreview = ({})
            return
        }
        const relationshipOption = root.relationshipOptions[relationshipCombo.currentIndex] || {}
        root._impactPreview = dependenciesController.previewCreateDependency({
            "taskId": taskId,
            "linkedTaskId": linkedTaskId,
            "relationshipDirection": String(relationshipOption.value || "PREDECESSOR"),
            "dependencyType": root.selectedDependencyTypeValue(),
            "lagDays": lagField.text
        }) || {}
    }

    // ── N8: relationship preview -- restates the user's own selection,
    // computes nothing about the schedule itself. ─────────────────────
    readonly property string _currentTaskLabel: String(root.taskState().name || root.taskData.title || "Current Task")
    readonly property string _relatedTaskLabel: {
        if (root.mode === "edit") {
            const state = root.dependencyState()
            return String(state.linkedTaskName || "Related task")
        }
        const taskOption = root.taskOptions[linkedTaskCombo.currentIndex] || {}
        return String(taskOption.label || "Select a task")
    }
    readonly property string _directionValue: root.mode === "edit"
        ? String(root.dependencyState().direction || "PREDECESSOR")
        : String((root.relationshipOptions[relationshipCombo.currentIndex] || {}).value || "PREDECESSOR")
    readonly property string _relationshipCode: {
        const opt = root.dependencyTypeOptions[dependencyTypeCombo.currentIndex] || {}
        return String(opt.label || "FS")
    }
    readonly property int _lagValue: parseInt(lagField.text || "0", 10) || 0
    readonly property string _lagLeadLabel: root._lagValue === 0
        ? "0d"
        : (root._lagValue > 0 ? ("+" + root._lagValue + "d lag") : (root._lagValue + "d lead"))

    AppControls.Label {
        Layout.fillWidth: true
        visible: root.mode === "create"
        text: String(root.taskData && root.taskData.title ? root.taskData.title : "Selected task")
        color: Theme.AppTheme.textPrimary
        font.family: Theme.AppTheme.fontFamily
        font.bold: true
        wrapMode: Text.WordWrap
    }

    GridLayout {
        Layout.fillWidth: true
        visible: root.mode === "create"
        columns: root.width > 520 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Direction"
            AppControls.ComboBox {
                id: relationshipCombo
                Layout.fillWidth: true
                model: root.relationshipOptions
                textRole: "label"
                onCurrentIndexChanged: Qt.callLater(root.runImpactPreview)
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Related Task"
            required: true
            AppControls.ComboBox {
                id: linkedTaskCombo
                Layout.fillWidth: true
                model: root.taskOptions
                textRole: "label"
                onCurrentIndexChanged: Qt.callLater(root.runImpactPreview)
            }
        }
    }

    AppControls.Label {
        Layout.fillWidth: true
        visible: root.mode === "edit"
        text: root._relatedTaskLabel
        color: Theme.AppTheme.textPrimary
        font.family: Theme.AppTheme.fontFamily
        font.bold: true
        wrapMode: Text.WordWrap
    }

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 520 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Relationship"
            AppControls.ComboBox {
                id: dependencyTypeCombo
                Layout.fillWidth: true
                model: root.dependencyTypeOptions
                textRole: "label"
                onCurrentIndexChanged: Qt.callLater(root.runImpactPreview)
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Lag / Lead (working days)"
            helperText: "Positive = lag. Negative = lead."
            AppControls.TextField {
                id: lagField
                Layout.fillWidth: true
                placeholderText: "0"
                inputMethodHints: Qt.ImhFormattedNumbersOnly
                onTextChanged: Qt.callLater(root.runImpactPreview)
            }
        }
    }

    AppControls.Label {
        Layout.fillWidth: true
        visible: root.mode === "create" && (root.taskOptions || []).length === 0
        text: "At least one other task must exist in this project before you can create a dependency."
        color: Theme.AppTheme.textSecondary
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.smallSize
        wrapMode: Text.WordWrap
    }

    // ── N8 relationship preview panel ───────────────────────────────────
    Rectangle {
        Layout.fillWidth: true
        implicitHeight: _relPreviewCol.implicitHeight + 16
        radius: Theme.AppTheme.radiusSm
        color: Theme.AppTheme.surfaceAlt
        border.color: Theme.AppTheme.divider
        border.width: 1

        ColumnLayout {
            id: _relPreviewCol
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
            spacing: 2

            AppControls.Label {
                Layout.fillWidth: true
                text: root._directionValue === "SUCCESSOR"
                    ? root._currentTaskLabel + "  - " + root._relationshipCode + (root._lagValue !== 0 ? " " + root._lagLeadLabel : "") + " -->  " + root._relatedTaskLabel
                    : root._relatedTaskLabel + "  - " + root._relationshipCode + (root._lagValue !== 0 ? " " + root._lagLeadLabel : "") + " -->  " + root._currentTaskLabel
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
                wrapMode: Text.WordWrap
            }
        }
    }

    // ── N9 schedule impact preview panel ────────────────────────────────
    Rectangle {
        id: impactPanel

        readonly property bool _available: root._impactPreview.available === true
        readonly property bool _isValid: root._impactPreview.isValid !== false
        readonly property string _riskLevel: String(root._impactPreview.riskLevel || "unknown")
        readonly property bool _elevatedRisk: _riskLevel === "medium" || _riskLevel === "high" || _riskLevel === "blocked"
        readonly property var _rows: root._impactPreview.rows || []

        Layout.fillWidth: true
        visible: impactPanel._available
        implicitHeight: visible ? _impactCol.implicitHeight + 16 : 0
        radius: Theme.AppTheme.radiusSm
        color: !impactPanel._isValid
            ? Theme.AppTheme.dangerSoft
            : impactPanel._elevatedRisk ? Theme.AppTheme.warningSoft : Theme.AppTheme.successSoft
        border.color: !impactPanel._isValid
            ? Theme.AppTheme.dangerSoftBorder
            : impactPanel._elevatedRisk ? Theme.AppTheme.warningSoftBorder : Theme.AppTheme.successSoftBorder
        border.width: 1

        ColumnLayout {
            id: _impactCol
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
            spacing: 4

            AppControls.Label {
                Layout.fillWidth: true
                text: "Schedule impact"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: String(root._impactPreview.summary || "")
                color: !impactPanel._isValid
                    ? Theme.AppTheme.danger
                    : impactPanel._elevatedRisk ? Theme.AppTheme.warning : Theme.AppTheme.success
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                visible: impactPanel._isValid && impactPanel._rows.length > 0
                columns: 2
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: 2

                AppControls.Label {
                    text: "Affected downstream tasks"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(root._impactPreview.affectedTaskCount || 0)
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                AppControls.Label {
                    text: "Largest shift"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }
                AppControls.Label {
                    text: String(root._impactPreview.largestShiftDays || 0) + " working days"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }

            Repeater {
                model: root._impactPreview.suggestions || []
                delegate: AppControls.Label {
                    id: _suggestionLabel
                    required property var modelData

                    Layout.fillWidth: true
                    text: "• " + String(_suggestionLabel.modelData)
                    color: impactPanel._elevatedRisk ? Theme.AppTheme.warning : Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
