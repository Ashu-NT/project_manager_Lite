import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

// Responsive table toolbar shared by every AdminEntityWorkspace and every
// other embedded/detail-page table workspace. Controls are grouped into a
// query cluster (search, custom filterContent, the generic Filters button),
// a table cluster (Columns, Views) and a command cluster (Refresh, Import,
// Export, the primary create/add action). At full width all three sit in
// one row; when the toolbar's own width can't fit that, the table+command
// clusters drop to a second row; if even that doesn't fit, Refresh/Columns/
// Views fold into a shared overflow menu and only the primary action stays
// directly visible. The breakpoints are computed from each control's own
// implicitWidth, not a fixed pixel constant, so this degrades correctly
// with any combination of filters/actions a caller wires up.
Rectangle {
    id: root

    property string searchText: ""
    property string searchPlaceholder: "Search..."
    property bool showSearch: true
    property bool showRefresh: true
    property bool showImport: false
    property bool showExport: false
    property bool showCreate: false
    property bool createEnabled: true
    property bool showFilter: false
    property bool showCustomize: false
    property bool showViews: false
    property string createLabel: "New"
    property bool isBusy: false
    property alias filterButtonItem: filterButton
    readonly property var customizeButtonItem: (root._needsOverflow && root.showCustomize) ? overflowButton : customizeButton
    readonly property var viewsButtonItem: (root._needsOverflow && root.showViews) ? overflowButton : viewsButton

    default property alias filterContent: filterSlot.data

    signal searchChanged(string text)
    signal filterClicked()
    signal customizeClicked()
    signal viewsClicked()
    signal refreshRequested()
    signal importRequested()
    signal exportRequested()
    signal createRequested()

    color: Theme.AppTheme.surfaceRaised
    radius: Theme.AppTheme.radiusMd
    implicitHeight: _rows.implicitHeight

    readonly property real _spacing: Theme.AppTheme.spacingSm
    readonly property real _horizontalMargin: Theme.AppTheme.marginMd
    readonly property real _searchMinWidth: 100
    // Absolute last-resort floor: search yields before filters do (filter
    // content is caller-owned and has no shared shrink API), but it never
    // collapses to nothing -- this keeps the field tappable/typeable even
    // when the query row's other content leaves very little room.
    readonly property real _searchAbsoluteFloor: 40
    readonly property real _searchFullWidth: 260

    function _sumWidths(widths) {
        const parts = widths.filter(function(w) { return w > 0 })
        if (parts.length === 0) return 0
        let total = 0
        for (let i = 0; i < parts.length; i += 1) total += parts[i]
        return total + (parts.length - 1) * root._spacing
    }

    readonly property real _queryNaturalWidth: root._sumWidths([
        root.showSearch ? root._searchFullWidth : 0,
        filterSlot.children.length > 0 ? filterSlot.implicitWidth : 0,
        root.showFilter ? filterButton.implicitWidth : 0
    ])
    readonly property real _tableNaturalWidth: root._sumWidths([
        root.showCustomize ? customizeButton.implicitWidth : 0,
        root.showViews ? viewsButton.implicitWidth : 0
    ])
    readonly property real _commandNaturalWidth: root._sumWidths([
        root.showRefresh ? refreshButton.implicitWidth : 0,
        root.showImport ? importButton.implicitWidth : 0,
        root.showExport ? exportButton.implicitWidth : 0,
        root.showCreate ? createButton.implicitWidth : 0
    ])

    readonly property real _wideRowWidth: root._sumWidths([root._queryNaturalWidth, root._tableNaturalWidth, root._commandNaturalWidth])
        + root._horizontalMargin * 2
    readonly property real _secondRowWidth: root._sumWidths([root._tableNaturalWidth, root._commandNaturalWidth])
        + root._horizontalMargin * 2

    readonly property bool _wide: root.width <= 0 || root.width >= root._wideRowWidth
    readonly property bool _needsOverflow: !root._wide && root.width < root._secondRowWidth
    readonly property string _layoutTier: root._wide ? "wide" : (root._needsOverflow ? "narrow" : "medium")

    // `_topRow`/`_bottomRow` are plain Items, not RowLayouts: a
    // QtQuick.Layouts container does not reliably re-measure a child that
    // is reparented into it after construction (the same failure mode
    // documented on SectionDetailPage's pinned-toolbar region), so instead
    // every control's `x` is positioned explicitly by `_relayoutRow()`
    // below, driven by each control's own (parent-independent)
    // implicitWidth. This also gives full, deterministic control over
    // left-to-right order, which independent `parent:` bindings do not
    // guarantee (they resolved in engine-determined order, not document
    // order, and produced a scrambled row).
    function _arrangeToolbar() {
        const tier = root._layoutTier
        filterSlot.parent = _topRow
        filterButton.parent = _topRow

        if (tier === "wide") {
            customizeButton.parent = _topRow
            viewsButton.parent = _topRow
            refreshButton.parent = _topRow
            importButton.parent = _topRow
            exportButton.parent = _topRow
            overflowButton.parent = _bottomRow
            createButton.parent = _topRow
        } else {
            customizeButton.parent = _bottomRow
            viewsButton.parent = _bottomRow
            refreshButton.parent = _bottomRow
            importButton.parent = _bottomRow
            exportButton.parent = _bottomRow
            overflowButton.parent = _bottomRow
            createButton.parent = _bottomRow
        }
        root._relayoutRows()
    }
    on_LayoutTierChanged: root._arrangeToolbar()

    function _packLeft(items, startX) {
        let x = startX
        for (let i = 0; i < items.length; i += 1) {
            const it = items[i]
            if (!it.visible || it.width <= 0) continue
            it.x = x
            x += it.width + root._spacing
        }
        return x
    }

    function _packRight(items, rowWidth) {
        let x = rowWidth
        for (let i = items.length - 1; i >= 0; i -= 1) {
            const it = items[i]
            if (!it.visible || it.width <= 0) continue
            x -= it.width
            it.x = x
            x -= root._spacing
        }
    }

    function _clusterWidth(items) {
        let w = 0
        for (let i = 0; i < items.length; i += 1) {
            const it = items[i]
            if (!it.visible || it.width <= 0) continue
            w += it.width + (w > 0 ? root._spacing : 0)
        }
        return w
    }

    function _relayoutRows() {
        if (root._wide) {
            const trailing = [refreshButton, importButton, exportButton, createButton]
            root._packRight(trailing, _topRow.width)
            const leading = [filterSlot, filterButton, customizeButton, viewsButton]
            const leadingWidth = root._clusterWidth(leading)
            const trailingWidth = root._clusterWidth(trailing)
            let searchWidth = 0
            if (searchInput.visible) {
                const reserved = leadingWidth + trailingWidth
                    + (leadingWidth > 0 ? root._spacing : 0)
                    + (trailingWidth > 0 ? root._spacing : 0)
                searchWidth = Math.max(root._searchMinWidth, Math.min(root._searchFullWidth, _topRow.width - reserved))
                searchInput.x = 0
                searchInput.width = searchWidth
            }
            root._packLeft(leading, searchInput.visible ? searchWidth + root._spacing : 0)
        } else {
            const queryExtras = [filterSlot, filterButton]
            const queryExtrasWidth = root._clusterWidth(queryExtras)
            if (searchInput.visible) {
                const reserved = queryExtrasWidth + (queryExtrasWidth > 0 ? root._spacing : 0)
                searchInput.x = 0
                searchInput.width = Math.max(root._searchAbsoluteFloor, _topRow.width - reserved)
            }
            root._packLeft(queryExtras, searchInput.visible ? searchInput.width + root._spacing : 0)

            const bottomLeading = [customizeButton, viewsButton]
            root._packLeft(bottomLeading, 0)
            const bottomTrailing = [overflowButton, refreshButton, importButton, exportButton, createButton]
            root._packRight(bottomTrailing, _bottomRow.width)
        }
    }

    // Recompute row positions whenever a control's own geometry actually
    // changes -- a tier switch already re-triggers via _arrangeToolbar().
    // This watches each control's own visible/width signals directly
    // (not an upstream `showX` flag) because reading a control's
    // `visible` from a handler on a *different* derived property can
    // observe a stale value while both are still settling from the same
    // underlying change; a control's own change signal never has that
    // problem for its own property.
    function _watchGeometry(item) {
        item.visibleChanged.connect(function() { root._relayoutRows() })
        item.widthChanged.connect(function() { root._relayoutRows() })
    }

    readonly property var _overflowItems: {
        const items = []
        if (root.showRefresh) items.push({ "id": "refresh", "label": "Refresh", "icon": "refresh", "enabled": !root.isBusy })
        if (root.showCustomize) items.push({ "id": "customize", "label": "Columns", "icon": "table_settings", "enabled": true })
        if (root.showViews) items.push({ "id": "views", "label": "Views", "icon": "register", "enabled": true })
        if (root.showImport) items.push({ "id": "import", "label": "Import", "icon": "export", "enabled": !root.isBusy })
        if (root.showExport) items.push({ "id": "export", "label": "Export", "icon": "upload", "enabled": !root.isBusy })
        return items
    }

    ColumnLayout {
        id: _rows
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: root._horizontalMargin
        anchors.rightMargin: root._horizontalMargin
        spacing: Theme.AppTheme.spacingXs

        Item {
            id: _topRow
            objectName: "toolbarTopRow"
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.AppTheme.toolbarHeight
            onWidthChanged: root._relayoutRows()

            AppControls.SearchField {
                id: searchInput
                objectName: "toolbarSearchField"
                visible: root.showSearch
                height: parent.height
                placeholderText: root.searchPlaceholder
                enabled: !root.isBusy
                debounceInterval: 280
                onSearchTriggered: function(text) {
                    root.searchChanged(text)
                }
            }
        }

        Item {
            id: _bottomRow
            objectName: "toolbarBottomRow"
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.AppTheme.toolbarHeight
            visible: !root._wide && (root._tableNaturalWidth > 0 || root._commandNaturalWidth > 0)
            onWidthChanged: root._relayoutRows()
        }
    }

    RowLayout {
        id: filterSlot
        objectName: "toolbarFilterSlot"
        spacing: root._spacing
    }

    Rectangle {
        id: filterButton
        objectName: "toolbarFilterButton"
        visible: root.showFilter
        implicitWidth: filterRow.implicitWidth + 14
        implicitHeight: Theme.AppTheme.inputHeight - 4

        radius: Theme.AppTheme.radiusSm
        color: filterHover.containsMouse
            ? Theme.AppTheme.hoverSurface
            : Theme.AppTheme.surfaceOverlay
        border.width: filterButton.activeFocus ? 2 : 0
        border.color: Theme.AppTheme.focusBorder

        activeFocusOnTab: root.showFilter
        Accessible.role: Accessible.Button
        Accessible.name: "Filters"
        Accessible.onPressAction: root.filterClicked()
        Keys.onPressed: (event) => {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                root.filterClicked()
                event.accepted = true
            }
        }

        Row {
            id: filterRow
            anchors.centerIn: parent
            spacing: Theme.AppTheme.spacingXs

            AppIcons.AppIcon {
                name: "filter"
                size: Theme.AppTheme.toolbarIconSize
                iconColor: Theme.AppTheme.textMuted
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Filters"
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        MouseArea {
            id: filterHover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.filterClicked()
        }
    }

    Rectangle {
        id: customizeButton
        objectName: "toolbarCustomizeButton"
        visible: root.showCustomize && !root._needsOverflow
        implicitWidth: customizeRow.implicitWidth + 14
        implicitHeight: Theme.AppTheme.inputHeight - 4

        radius: Theme.AppTheme.radiusSm
        color: customizeHover.containsMouse
            ? Theme.AppTheme.hoverSurface
            : Theme.AppTheme.surfaceOverlay
        border.width: customizeButton.activeFocus ? 2 : 0
        border.color: Theme.AppTheme.focusBorder

        activeFocusOnTab: customizeButton.visible
        Accessible.role: Accessible.Button
        Accessible.name: "Columns"
        Accessible.onPressAction: root.customizeClicked()
        Keys.onPressed: (event) => {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                root.customizeClicked()
                event.accepted = true
            }
        }

        Row {
            id: customizeRow
            anchors.centerIn: parent
            spacing: Theme.AppTheme.spacingXs

            AppIcons.AppIcon {
                name: "table_settings"
                size: Theme.AppTheme.toolbarIconSize
                iconColor: Theme.AppTheme.textMuted
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Columns"
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        MouseArea {
            id: customizeHover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.customizeClicked()
        }
    }

    Rectangle {
        id: viewsButton
        objectName: "toolbarViewsButton"
        visible: root.showViews && !root._needsOverflow
        implicitWidth: viewsRow.implicitWidth + 14
        implicitHeight: Theme.AppTheme.inputHeight - 4

        radius: Theme.AppTheme.radiusSm
        color: viewsHover.containsMouse
            ? Theme.AppTheme.hoverSurface
            : Theme.AppTheme.surfaceOverlay
        border.width: viewsButton.activeFocus ? 2 : 0
        border.color: Theme.AppTheme.focusBorder

        activeFocusOnTab: viewsButton.visible
        Accessible.role: Accessible.Button
        Accessible.name: "Views"
        Accessible.onPressAction: root.viewsClicked()
        Keys.onPressed: (event) => {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                root.viewsClicked()
                event.accepted = true
            }
        }

        Row {
            id: viewsRow
            anchors.centerIn: parent
            spacing: Theme.AppTheme.spacingXs

            AppIcons.AppIcon {
                name: "register"
                size: Theme.AppTheme.toolbarIconSize
                iconColor: Theme.AppTheme.textMuted
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Views"
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        MouseArea {
            id: viewsHover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.viewsClicked()
        }
    }

    AppControls.SecondaryButton {
        id: refreshButton
        objectName: "toolbarRefreshButton"
        visible: root.showRefresh && !root._needsOverflow
        text: "Refresh"
        iconName: "refresh"
        enabled: !root.isBusy
        implicitWidth: 88
        onClicked: root.refreshRequested()
    }

    AppControls.SecondaryButton {
        id: importButton
        objectName: "toolbarImportButton"
        visible: root.showImport && !root._needsOverflow
        text: "Import"
        iconName: "export"
        enabled: !root.isBusy
        implicitWidth: 88
        onClicked: root.importRequested()
    }

    AppControls.SecondaryButton {
        id: exportButton
        objectName: "toolbarExportButton"
        visible: root.showExport && !root._needsOverflow
        text: "Export"
        iconName: "upload"
        enabled: !root.isBusy
        implicitWidth: 88
        onClicked: root.exportRequested()
    }

    ActionsMenuButton {
        id: overflowButton
        objectName: "toolbarOverflowButton"
        visible: root._needsOverflow && root._overflowItems.length > 0
        triggerLabel: "More"
        items: root._overflowItems
        onActionSelected: function(id) {
            if (id === "refresh") root.refreshRequested()
            else if (id === "import") root.importRequested()
            else if (id === "export") root.exportRequested()
            else if (id === "customize") root.customizeClicked()
            else if (id === "views") root.viewsClicked()
        }
    }

    AppControls.PrimaryButton {
        id: createButton
        objectName: "toolbarCreateButton"
        visible: root.showCreate
        text: root.createLabel
        iconName: "add"
        enabled: !root.isBusy && root.createEnabled
        onClicked: root.createRequested()
    }

    onSearchTextChanged: {
        if (searchInput.text !== root.searchText) {
            searchInput.text = root.searchText
        }
    }

    Component.onCompleted: {
        if (searchInput.text !== root.searchText) {
            searchInput.text = root.searchText
        }
        root._watchGeometry(searchInput)
        root._watchGeometry(filterSlot)
        root._watchGeometry(filterButton)
        root._watchGeometry(customizeButton)
        root._watchGeometry(viewsButton)
        root._watchGeometry(refreshButton)
        root._watchGeometry(importButton)
        root._watchGeometry(exportButton)
        root._watchGeometry(overflowButton)
        root._watchGeometry(createButton)
        root._arrangeToolbar()
    }
}
