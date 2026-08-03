import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

Item {
    id: root

    property alias text: field.text
    property alias placeholderText: field.placeholderText
    property alias inputMethodHints: field.inputMethodHints
    property alias validator: field.validator
    property alias readOnly: field.readOnly
    property alias font: field.font
    property string format: "yyyy-MM-dd"
    property int minimumYear: new Date().getFullYear() - 15
    property int maximumYear: new Date().getFullYear() + 15
    property var selectedDate: _parseDate(field.text)

    property Item popupBoundaryItem: null
    
    signal accepted()
    signal dateSelected(string text)

    implicitWidth: 180
    implicitHeight: Theme.AppTheme.inputHeight

    function _pad(value) {
        return String(value).padStart(2, "0")
    }

    function _daysInMonth(year, monthIndex) {
        return new Date(year, monthIndex + 1, 0).getDate()
    }

    function _parseDate(text) {
        const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(text || "").trim())
        if (!match) {
            return null
        }
        const year = Number(match[1])
        const month = Number(match[2]) - 1
        const day = Number(match[3])
        const parsed = new Date(year, month, day)
        if (parsed.getFullYear() !== year || parsed.getMonth() !== month || parsed.getDate() !== day) {
            return null
        }
        return parsed
    }

    function _monthOptions() {
        return [
            { "value": 0, "label": "January" },
            { "value": 1, "label": "February" },
            { "value": 2, "label": "March" },
            { "value": 3, "label": "April" },
            { "value": 4, "label": "May" },
            { "value": 5, "label": "June" },
            { "value": 6, "label": "July" },
            { "value": 7, "label": "August" },
            { "value": 8, "label": "September" },
            { "value": 9, "label": "October" },
            { "value": 10, "label": "November" },
            { "value": 11, "label": "December" }
        ]
    }

    function _yearOptions() {
        const values = []
        for (let year = root.minimumYear; year <= root.maximumYear; year += 1) {
            values.push({ "value": year, "label": String(year) })
        }
        return values
    }

    function _dayOptions() {
        const totalDays = root._daysInMonth(_pickerYear, _pickerMonth)
        const values = []
        for (let day = 1; day <= totalDays; day += 1) {
            values.push({ "value": day, "label": root._pad(day) })
        }
        return values
    }

    function _applyDate(year, monthIndex, day) {
        const nextDate = new Date(year, monthIndex, day)
        field.text = Qt.formatDate(nextDate, root.format)
        root.dateSelected(field.text)
    }

    function _syncPickerState(baseDate) {
        const source = baseDate || root.selectedDate || new Date()
        _pickerYear = source.getFullYear()
        _pickerMonth = source.getMonth()
        _pickerDay = source.getDate()
    }

    function _effectivePopupBoundary() {
        return root.popupBoundaryItem || QQC2.Overlay.overlay
    }

    function _popupBounds() {
        const overlay = QQC2.Overlay.overlay
        const boundary = root._effectivePopupBoundary()
        const margin = Theme.AppTheme.spacingSm

        const topLeft = boundary.mapToItem(overlay, 0, 0)

        return {
            "x": topLeft.x + margin,
            "y": topLeft.y + margin,
            "width": Math.max(
                180,
                boundary.width - margin * 2
            ),
            "height": Math.max(
                180,
                boundary.height - margin * 2
            )
        }
    }

    function _popupWidth() {
        const bounds = root._popupBounds()
        return Math.max(180, Math.min(Math.max(root.width, 280), bounds.width))
    }

    function _positionPopup() {
        const overlay = QQC2.Overlay.overlay
        const bounds = root._popupBounds()
        const margin = Theme.AppTheme.spacingXs

        const popupWidth = datePopup.width
        const popupHeight = datePopup.implicitHeight > 0
            ? datePopup.implicitHeight
            : datePopup.height

        const anchorTop = root.mapToItem(
            overlay,
            0,
            0
        )

        const anchorBottom = root.mapToItem(
            overlay,
            0,
            root.height
        )

        // Prefer left alignment with the field.
        let nextX = anchorTop.x
        let nextY = anchorBottom.y + margin

        // Shift left when the popup would exceed the right boundary.
        const maximumX =
            bounds.x + bounds.width - popupWidth

        nextX = Math.max(
            bounds.x,
            Math.min(nextX, maximumX)
        )

        // Prefer below; move above when there is insufficient room.
        if (nextY + popupHeight > bounds.y + bounds.height) {
            const aboveY =
                anchorTop.y - popupHeight - margin

            if (aboveY >= bounds.y) {
                nextY = aboveY
            } else {
                nextY = Math.max(
                    bounds.y,
                    bounds.y + bounds.height - popupHeight
                )
            }
        }

        datePopup.x = Math.round(nextX)
        datePopup.y = Math.round(nextY)
    }

    property int _pickerYear: (new Date()).getFullYear()
    property int _pickerMonth: (new Date()).getMonth()
    property int _pickerDay: (new Date()).getDate()

    Rectangle {
        anchors.fill: parent
        radius: Theme.AppTheme.radiusSm
        color: field.enabled
            ? Theme.AppTheme.surfaceRaised
            : Theme.AppTheme.surfaceOverlay
        border.width: 1
        border.color: field.activeFocus
            ? Theme.AppTheme.focusBorder
            : hoverHandler.hovered
                ? Theme.AppTheme.borderStrong
                : Theme.AppTheme.subtleBorder
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.spacingSm
        anchors.rightMargin: Theme.AppTheme.spacingSm
        spacing: Theme.AppTheme.spacingXs

        TextField {
            id: field
            Layout.fillWidth: true
            enabled: root.enabled
            background: Item {}
            leftPadding: 0
            rightPadding: 0
            topPadding: 0
            bottomPadding: 0

            onEditingFinished: {
                const parsed = root._parseDate(text)
                if (parsed) {
                    text = Qt.formatDate(parsed, root.format)
                    root._syncPickerState(parsed)
                }
            }

            onAccepted: root.accepted()
        }

        AppIcons.AppIcon {
            name: "calendar"
            size: Theme.AppTheme.toolbarIconSize
            iconColor: pickerHover.hovered
                ? Theme.AppTheme.textSecondary
                : Theme.AppTheme.textMuted

            HoverHandler {
                id: pickerHover
                enabled: root.enabled && parent.visible
            }

            TapHandler {
                enabled: root.enabled && parent.visible
                onTapped: {
                    root._syncPickerState(root.selectedDate)
                    datePopup.open()
                }
            }
        }
    }

    HoverHandler {
        id: hoverHandler
    }

    QQC2.Popup {
        id: datePopup

        parent: QQC2.Overlay.overlay

        width: root._popupWidth()
        padding: Theme.AppTheme.dialogPadding

        closePolicy:
            QQC2.Popup.CloseOnEscape
            | QQC2.Popup.CloseOnPressOutside

        background: Rectangle {
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.dialogBackground
            border.color: Theme.AppTheme.dialogBorder
            border.width: 1
        }

        onAboutToShow: {
            root._syncPickerState(root.selectedDate)
            Qt.callLater(root._positionPopup)
        }

        onWidthChanged: {
            if (visible)
                Qt.callLater(root._positionPopup)
        }

        onHeightChanged: {
            if (visible)
                Qt.callLater(root._positionPopup)
        }

        contentItem: ColumnLayout {
            width: datePopup.availableWidth
            spacing: Theme.AppTheme.spacingSm

            Label {
                text: "Choose Date"
                font.bold: true
                font.pixelSize: Theme.AppTheme.sectionTitleSize
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: Theme.AppTheme.spacingSm

                ComboBox {
                    id: monthCombo

                    Layout.fillWidth: true
                    Layout.minimumWidth: 0

                    model: root._monthOptions()
                    textRole: "label"
                    currentIndex: root._pickerMonth

                    onActivated: function(index) {
                        root._pickerMonth = Number(
                            (model[index] || { "value": 0 }).value || 0
                        )

                        const maxDay = root._daysInMonth(
                            root._pickerYear,
                            root._pickerMonth
                        )

                        if (root._pickerDay > maxDay)
                            root._pickerDay = maxDay
                    }
                }

                ComboBox {
                    id: dayCombo

                    Layout.preferredWidth: 72
                    Layout.minimumWidth: 58
                    Layout.maximumWidth: 78

                    model: root._dayOptions()
                    textRole: "label"
                    currentIndex: Math.max(0, root._pickerDay - 1)

                    onActivated: function(index) {
                        const options = root._dayOptions()

                        root._pickerDay = Number(
                            (options[index] || { "value": 1 }).value || 1
                        )
                    }
                }

                ComboBox {
                    id: yearCombo

                    Layout.preferredWidth: 88
                    Layout.minimumWidth: 74
                    Layout.maximumWidth: 96

                    model: root._yearOptions()
                    textRole: "label"
                    currentIndex: Math.max(
                        0,
                        root._pickerYear - root.minimumYear
                    )

                    onActivated: function(index) {
                        root._pickerYear = Number(
                            (
                                model[index]
                                || { "value": new Date().getFullYear() }
                            ).value
                            || new Date().getFullYear()
                        )

                        const maxDay = root._daysInMonth(
                            root._pickerYear,
                            root._pickerMonth
                        )

                        if (root._pickerDay > maxDay)
                            root._pickerDay = maxDay
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: Theme.AppTheme.spacingSm

                SecondaryButton {
                    text: "Today"
                    iconName: "calendar"

                    Layout.fillWidth: true
                    Layout.minimumWidth: 0

                    onClicked: {
                        const today = new Date()

                        root._applyDate(
                            today.getFullYear(),
                            today.getMonth(),
                            today.getDate()
                        )

                        datePopup.close()
                    }
                }

                SecondaryButton {
                    text: "Clear"
                    iconName: "close"

                    Layout.fillWidth: true
                    Layout.minimumWidth: 0

                    onClicked: {
                        field.clear()
                        root.dateSelected("")
                        datePopup.close()
                    }
                }

                PrimaryButton {
                    text: "Apply"
                    iconName: "approve"

                    Layout.fillWidth: true
                    Layout.minimumWidth: 0

                    onClicked: {
                        root._applyDate(
                            root._pickerYear,
                            root._pickerMonth,
                            root._pickerDay
                        )

                        datePopup.close()
                    }
                }
            }
        }
    }
}
