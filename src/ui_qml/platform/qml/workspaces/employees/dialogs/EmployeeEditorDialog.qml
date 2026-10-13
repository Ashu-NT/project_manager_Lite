import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var siteOptions: []
    // Each entry also carries siteId/siteName (see build_department_options)
    // -- used to resolve/lock the Site field the moment a Site-bound
    // Department is chosen.
    property var departmentOptions: []
    property var workspaceController: null
    property string employeeCode: ""

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: Theme.AppTheme.dialogWidthStandard
    title: root.mode === "create" ? "New Employee" : "Edit Employee"
    primaryText: root.mode === "create" ? "Create" : "Save"
    primaryIcon: root.mode === "create" ? "add" : "save"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function submitDialog() {
        if (root.employeeCode.trim().length === 0) {
            root.errorMessage = "Employee number is required."
            return
        }
        if (fullNameField.text.trim().length === 0) {
            root.errorMessage = "Employee name is required."
            return
        }
        if (root._currentValue(departmentModel, departmentCombo).length === 0) {
            root.errorMessage = "Department is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.mode, root.formData)
    }

    // Lifecycle (Active/Inactive) is never editable here -- new employees
    // always start ACTIVE, and existing ones change state only through the
    // dedicated Activate/Deactivate actions (Inspector/Detail Actions ▾).
    // System Access (User Account) is a separate relationship operation
    // (link_employee_user_account/unlink_employee_user_account), never a
    // field on ordinary profile Create/Edit.
    readonly property var formData: ({
        employeeId: root.draft.employeeId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        employeeCode: root.employeeCode.trim(),
        fullName: fullNameField.text.trim(),
        departmentId: root._currentValue(departmentModel, departmentCombo),
        departmentName: root._currentLabel(departmentModel, departmentCombo),
        siteId: root._currentValue(siteModel, siteCombo),
        siteName: root._currentLabel(siteModel, siteCombo),
        title: titleField.text.trim(),
        employmentType: root._currentValue(employmentTypeModel, employmentTypeCombo) || "FULL_TIME",
        email: emailField.text.trim(),
        phone: phoneField.text.trim()
    })

    function openForCreate(options) {
        root.mode = "create"
        root.draft = ({})
        _assignOptions(options || ({}))
        _loadDraft()
        open()
    }

    function openForEdit(draftData, options) {
        root.mode = "edit"
        root.draft = draftData || ({})
        _assignOptions(options || ({}))
        _loadDraft()
        open()
    }

    function _assignOptions(options) {
        root.siteOptions = options.siteOptions || []
        root.departmentOptions = options.departmentOptions || []
        _reloadSiteModel()
        _reloadDepartmentModel()
    }

    function _reloadSiteModel() {
        siteModel.clear()
        siteModel.append({ label: "Not set", value: "" })
        for (let index = 0; index < root.siteOptions.length; index += 1) {
            const option = root.siteOptions[index]
            siteModel.append({ label: option.label || "", value: option.value || "" })
        }
    }

    function _reloadDepartmentModel() {
        departmentModel.clear()
        departmentModel.append({ label: "Select a department", value: "", siteId: "", siteName: "" })
        for (let index = 0; index < root.departmentOptions.length; index += 1) {
            const option = root.departmentOptions[index]
            departmentModel.append({
                label: option.label || "",
                value: option.value || "",
                siteId: option.siteId || "",
                siteName: option.siteName || ""
            })
        }
    }

    function _loadDraft() {
        root.employeeCode = root.draft.employeeCode || ""
        fullNameField.text = root.draft.fullName || ""
        titleField.text = root.draft.title || ""
        emailField.text = root.draft.email || ""
        phoneField.text = root.draft.phone || ""
        _setCurrentIndex(departmentModel, departmentCombo, root.draft.departmentId || "")
        _setCurrentIndex(siteModel, siteCombo, root.draft.siteId || "")
        _setCurrentIndex(employmentTypeModel, employmentTypeCombo, root.draft.employmentType || "FULL_TIME")
        root._applyDepartmentSiteConstraint()
    }

    // -- Department/Site dependency: when the selected Department is bound
    // to a Site, the Site field locks to that exact Site (matching
    // resolve_employee_site_for_department's own backend invariant) so an
    // invalid combination can never even be submitted; when the Department
    // is organization-wide, Site stays freely selectable from any
    // same-organization Site. Backend validation remains authoritative --
    // this is a UX-level prevention only.
    property bool siteLockedByDepartment: false

    function _applyDepartmentSiteConstraint() {
        if (departmentCombo.currentIndex < 0 || departmentCombo.currentIndex >= departmentModel.count) {
            root.siteLockedByDepartment = false
            return
        }
        const entry = departmentModel.get(departmentCombo.currentIndex)
        const siteId = String(entry.siteId || "")
        if (siteId.length > 0) {
            root.siteLockedByDepartment = true
            _setCurrentIndex(siteModel, siteCombo, siteId)
        } else {
            root.siteLockedByDepartment = false
        }
    }

    function _setCurrentIndex(model, combo, value) {
        for (let index = 0; index < model.count; index += 1) {
            if (model.get(index).value === value) {
                combo.currentIndex = index
                return
            }
        }
        combo.currentIndex = 0
    }

    function _currentValue(model, combo) {
        if (combo.currentIndex < 0 || combo.currentIndex >= model.count) {
            return ""
        }
        return model.get(combo.currentIndex).value || ""
    }

    function _currentLabel(model, combo) {
        if (combo.currentIndex <= 0 || combo.currentIndex >= model.count) {
            return ""
        }
        return model.get(combo.currentIndex).label || ""
    }

    ListModel { id: siteModel }
    ListModel { id: departmentModel }
    ListModel {
        id: employmentTypeModel

        ListElement { label: "Full Time"; value: "FULL_TIME" }
        ListElement { label: "Part Time"; value: "PART_TIME" }
        ListElement { label: "Contractor"; value: "CONTRACTOR" }
        ListElement { label: "Temporary"; value: "TEMPORARY" }
    }

    // ── IDENTITY ─────────────────────────────────────────────────────────
    AppWidgets.SectionHeading {
        Layout.fillWidth: true
        label: "Identity"
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Employee Name"
        required: true

        AppControls.TextField {
            id: fullNameField
            Layout.fillWidth: true
            placeholderText: "e.g. Jane Smith"
        }
    }

    AppWidgets.CodeFieldRow {
        Layout.fillWidth: true
        label: "Employee Number"
        value: root.employeeCode
        placeholderText: "Auto-generated if empty"
        required: true
        generateVisible: true
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onValueEdited: function(code) { root.employeeCode = code }
        onGenerateRequested: {
            if (root.workspaceController) {
                const suggested = root.workspaceController.generateEntityCode("employee", root.formData)
                if (suggested && suggested.length > 0) {
                    root.employeeCode = suggested
                }
            }
        }
    }

    // ── EMPLOYMENT ───────────────────────────────────────────────────────
    AppWidgets.SectionHeading {
        Layout.fillWidth: true
        label: "Employment"
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Job Title"

            AppControls.TextField {
                id: titleField
                Layout.fillWidth: true
                placeholderText: "e.g. Maintenance Lead"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Employment Type"

            AppControls.ComboBox {
                id: employmentTypeCombo
                Layout.fillWidth: true
                model: employmentTypeModel
                textRole: "label"
            }
        }
    }

    // ── ORGANIZATIONAL ASSIGNMENT ────────────────────────────────────────
    // Department is required (Employee.department_id is a required
    // domain field). Site is optional and its available range depends on
    // the selected Department -- see _applyDepartmentSiteConstraint above.
    AppWidgets.SectionHeading {
        Layout.fillWidth: true
        label: "Organizational Assignment"
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Department"
        required: true

        AppControls.ComboBox {
            id: departmentCombo
            Layout.fillWidth: true
            model: departmentModel
            textRole: "label"
            onActivated: root._applyDepartmentSiteConstraint()
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Site"

        AppControls.ComboBox {
            id: siteCombo
            Layout.fillWidth: true
            model: siteModel
            textRole: "label"
            enabled: !root.siteLockedByDepartment
        }
    }

    AppControls.Label {
        Layout.fillWidth: true
        visible: root.siteLockedByDepartment
        text: "Site is determined by the selected department."
        color: Theme.AppTheme.textMuted
        font.pixelSize: Theme.AppTheme.captionSize
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
    }

    // ── CONTACT ──────────────────────────────────────────────────────────
    AppWidgets.SectionHeading {
        Layout.fillWidth: true
        label: "Contact"
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Email"

            AppControls.TextField {
                id: emailField
                Layout.fillWidth: true
                placeholderText: "name@company.com"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Phone"

            AppControls.TextField {
                id: phoneField
                Layout.fillWidth: true
                placeholderText: "+1 555 0100"
            }
        }
    }
}
