pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme

Item {
    id: root

    property var    dependenciesModel: AppMock.MockFactory.catalog()
    property var    dependenciesTableModel: null
    property bool   isBusy: false
    property bool   canCreate: false
    property string errorText: ""
    property var    dependencyTypeOptions: []

    signal createRequested()
    signal editRequested(var dependencyData)
    signal deleteRequested(var dependencyData)
    signal selectionChanged(var dependencyData)

    readonly property var _items: root.dependenciesModel.items || []
    property string _selectedId: ""
    function _itemForId(dependencyId) {
        const id = String(dependencyId || "")
        if (!id.length) return null
        const list = root._items
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].id || "") === id) return list[i]
        }
        return null
    }
    readonly property var _selectedItem: root._itemForId(root._selectedId)

    readonly property int _tableH: {
        const n = root._items.length
        const rH = Theme.AppTheme.compactRowHeight
        const hH = Theme.AppTheme.normalRowHeight
        const natural = hH + Math.max(n, 1) * rH + 12
        return Math.max(200, Math.min(natural, 320))
    }

    readonly property var _columns: [
        { key: "title",       label: "Task",   flex: 3,   sortable: false },
        { key: "subtitle",    label: "Type",   flex: 1.5, sortable: false },
        { key: "metaText",    label: "Lag",    flex: 1,   sortable: false },
        { key: "statusLabel", label: "Status", flex: 0,   minWidth: 90, type: "status" }
    ]

    function openEditSelected() {
        if (root._selectedItem) {
            _editPopup.openForItem(root._selectedItem)
        }
    }

    implicitHeight: _col.implicitHeight

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 0

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.errorText.length > 0
            tone: "danger"
            message: root.errorText
        }

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Dependencies"
            subtitle: root._items.length > 0 ? String(root._items.length) : ""
            busy: root.isBusy
            createLabel: root.canCreate ? "Add Dependency" : ""
            actions: []
            onCreateRequested: root.createRequested()
        }

        Item {
            Layout.fillWidth: true
            height: root._tableH

            AppWidgets.DataTable {
                anchors.fill: parent
                columns: root._columns
                sourceModel: root.dependenciesTableModel
                selectedRowId: root._selectedId
                loading: root.isBusy
                emptyText: root.dependenciesModel.emptyState || "No dependencies for this task."

                onRowSelected: function(rowId) {
                    root._selectedId = rowId
                    root.selectionChanged(root._itemForId(rowId))
                }
                onRowActivated: function(rowId) {
                    root._selectedId = rowId
                    root.selectionChanged(root._itemForId(rowId))
                }
            }
        }

        AppWidgets.EntityDialog {
            id: _editPopup
            title: "Edit Dependency"

            property var _item: null

            function openForItem(item) {
                _item = item
                const state = item.state || {}
                const typeVal = String(state.dependencyType || "FS")
                const opts = root.dependencyTypeOptions || []
                _typeCombo.currentIndex = -1
                for (let i = 0; i < opts.length; i++) {
                    if (String(opts[i].value || "") === typeVal) {
                        _typeCombo.currentIndex = i
                        break
                    }
                }
                _lagField.text = String(state.lagDays || "0")
                _editError.message = ""
                open()
            }

            contentItem: ColumnLayout {
                spacing: Theme.AppTheme.spacingSm
                implicitWidth: 300

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Dependency Type"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.ComboBox {
                    id: _typeCombo
                    Layout.fillWidth: true
                    model: root.dependencyTypeOptions
                    textRole: "label"
                    enabled: !root.isBusy
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Lag Days"
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                AppControls.TextField {
                    id: _lagField
                    Layout.fillWidth: true
                    placeholderText: "0"
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    enabled: !root.isBusy
                }

                AppWidgets.InlineMessage {
                    id: _editError
                    Layout.fillWidth: true
                    tone: "danger"
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.SecondaryButton {
                        Layout.fillWidth: true
                        text: "Cancel"
                        enabled: !root.isBusy
                        onClicked: _editPopup.close()
                    }

                    AppControls.PrimaryButton {
                        Layout.fillWidth: true
                        text: "Save"
                        iconName: "approve"
                        enabled: _typeCombo.currentIndex >= 0 && !root.isBusy
                        onClicked: {
                            if (!_editPopup._item) return
                            const state = _editPopup._item.state || {}
                            const opts = root.dependencyTypeOptions || []
                            const selected = opts[_typeCombo.currentIndex]
                            if (!selected) return
                            _editError.message = ""
                            root.editRequested({
                                "dependencyId": String(state.dependencyId || _editPopup._item.id || ""),
                                "dependencyType": String(selected.value || "FS"),
                                "lagDays": parseInt(_lagField.text || "0", 10) || 0
                            })
                            _editPopup.close()
                        }
                    }
                }
            }
        }
    }
}
