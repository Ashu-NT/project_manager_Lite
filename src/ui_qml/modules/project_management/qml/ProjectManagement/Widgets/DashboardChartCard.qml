pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property string chartType: "bar"
    property string emptyState: ""
    property var points: []

    readonly property real maxValue: root.computeMaxValue()
    readonly property real minValue: root.computeMinValue()
    readonly property var lineAxisBounds: root.buildLineAxisBounds()
    readonly property var lineAxisTicks: root.buildLineAxisTicks()

    function computeMaxValue() {
        const rows = root.points || []
        let maxValue = 1
        for (let index = 0; index < rows.length; index += 1) {
            const point = rows[index]
            maxValue = Math.max(maxValue, Number(point.value || 0))
            if (point.targetValue !== undefined && point.targetValue !== null) {
                maxValue = Math.max(maxValue, Number(point.targetValue || 0))
            }
        }
        return maxValue
    }

    function toneColor(tone) {
        switch (String(tone || "")) {
        case "danger":
            return Theme.AppTheme.danger
        case "warning":
            return Theme.AppTheme.warning
        case "success":
            return Theme.AppTheme.success
        default:
            return Theme.AppTheme.accent
        }
    }

    function computeMinValue() {
        const rows = root.points || []
        let minValue = 0
        let hasValue = false
        for (let index = 0; index < rows.length; index += 1) {
            const point = rows[index]
            const value = Number(point.value || 0)
            if (!hasValue) {
                minValue = value
                hasValue = true
            } else {
                minValue = Math.min(minValue, value)
            }
            if (point.targetValue !== undefined && point.targetValue !== null) {
                minValue = Math.min(minValue, Number(point.targetValue || 0))
            }
        }
        return hasValue ? minValue : 0
    }

    function niceNumber(value, roundValue) {
        const safeValue = Math.max(Math.abs(Number(value || 0)), 1)
        const exponent = Math.floor(Math.log(safeValue) / Math.LN10)
        const fraction = safeValue / Math.pow(10, exponent)
        let niceFraction = 1

        if (roundValue) {
            if (fraction < 1.5) {
                niceFraction = 1
            } else if (fraction < 3) {
                niceFraction = 2
            } else if (fraction < 7) {
                niceFraction = 5
            } else {
                niceFraction = 10
            }
        } else if (fraction <= 1) {
            niceFraction = 1
        } else if (fraction <= 2) {
            niceFraction = 2
        } else if (fraction <= 5) {
            niceFraction = 5
        } else {
            niceFraction = 10
        }

        return niceFraction * Math.pow(10, exponent)
    }

    function buildLineAxisBounds() {
        const rows = root.points || []
        if (!rows.length) {
            return {
                min: 0,
                max: 1,
                step: 0.5,
            }
        }

        let minValue = root.minValue
        let maxValue = root.maxValue
        if (maxValue === minValue) {
            const padding = Math.max(Math.abs(maxValue) * 0.15, 1)
            minValue -= padding
            maxValue += padding
        } else {
            const span = maxValue - minValue
            const padding = Math.max(span * 0.12, 1)
            minValue -= padding
            maxValue += padding
        }

        const targetTickCount = 4
        const niceRange = root.niceNumber(maxValue - minValue, false)
        const step = root.niceNumber(niceRange / Math.max(targetTickCount - 1, 1), true)
        const axisMin = Math.floor(minValue / step) * step
        const axisMax = Math.ceil(maxValue / step) * step
        return {
            min: axisMin,
            max: axisMax,
            step: step,
        }
    }

    function buildLineAxisTicks() {
        const bounds = root.lineAxisBounds
        const ticks = []
        const step = Math.max(Number(bounds.step || 0), 1e-9)
        for (
            let value = Number(bounds.max || 0);
            value >= Number(bounds.min || 0) - (step / 2);
            value -= step
        ) {
            ticks.push(value)
        }
        return ticks.length > 0 ? ticks : [Number(bounds.max || 1), Number(bounds.min || 0)]
    }

    function formatAxisValue(value) {
        const number = Number(value || 0)
        const absolute = Math.abs(number)
        if (absolute >= 1000000) {
            return (number / 1000000).toFixed(1).replace(/\.0$/, "") + "M"
        }
        if (absolute >= 1000) {
            return (number / 1000).toFixed(1).replace(/\.0$/, "") + "K"
        }
        if (absolute >= 100) {
            return String(Math.round(number))
        }
        return number.toFixed(number % 1 === 0 ? 0 : 1)
    }

    implicitWidth: 420
    implicitHeight: contentColumn.implicitHeight

    onPointsChanged: lineCanvas.requestPaint()
    onWidthChanged: lineCanvas.requestPaint()
    onHeightChanged: lineCanvas.requestPaint()

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs
            visible: root.title.length > 0 || root.subtitle.length > 0

            Label {
                Layout.fillWidth: true
                visible: root.title.length > 0
                text: root.title
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                visible: root.subtitle.length > 0
                text: root.subtitle
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        Label {
            Layout.fillWidth: true
            visible: (root.points || []).length === 0 && root.emptyState.length > 0
            text: root.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 244
            visible: root.chartType === "line" && (root.points || []).length > 0
            spacing: Theme.AppTheme.spacingXs

            Item {
                id: yAxisLabelColumn

                Layout.preferredWidth: 48
                Layout.fillHeight: true

                Repeater {
                    model: root.lineAxisTicks

                    delegate: Label {
                        required property var modelData
                        required property int index

                        x: 0
                        y: (yAxisLabelColumn.height - height) * (
                            index / Math.max(root.lineAxisTicks.length - 1, 1)
                        )
                        text: root.formatAxisValue(modelData)
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: index === 0 || index === root.lineAxisTicks.length - 1
                        elide: Text.ElideRight
                        width: yAxisLabelColumn.width
                        horizontalAlignment: Text.AlignRight
                        rightPadding: 2
                    }
                }
            }

            Canvas {
                id: lineCanvas

                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 244
                implicitHeight: 300

                onPaint: {
                    const ctx = getContext("2d")
                    const rows = root.points || []
                    ctx.reset()
                    ctx.clearRect(0, 0, width, height)
                    if (!rows.length) {
                        return
                    }

                    const left = 10
                    const right = 16
                    const top = 12
                    const bottom = 10
                    const plotWidth = Math.max(1, width - left - right)
                    const plotHeight = Math.max(1, height - top - bottom)
                    const denominator = Math.max(rows.length - 1, 1)
                    const axisMin = Number(root.lineAxisBounds.min || 0)
                    const axisMax = Number(root.lineAxisBounds.max || 1)
                    const axisSpan = Math.max(axisMax - axisMin, 1e-9)
                    const axisBottom = top + plotHeight

                    function xFor(index) {
                        return left + (plotWidth * index / denominator)
                    }

                    function yFor(value) {
                        return top + plotHeight - (((Number(value || 0) - axisMin) / axisSpan) * plotHeight)
                    }

                    ctx.strokeStyle = Theme.AppTheme.divider
                    ctx.lineWidth = 1
                    for (let grid = 0; grid < root.lineAxisTicks.length; grid += 1) {
                        const y = yFor(root.lineAxisTicks[grid])
                        ctx.beginPath()
                        ctx.moveTo(left, y)
                        ctx.lineTo(width - right, y)
                        ctx.stroke()
                    }

                    ctx.strokeStyle = Theme.AppTheme.textSecondary
                    ctx.lineWidth = 1.5
                    ctx.beginPath()
                    ctx.moveTo(left, top)
                    ctx.lineTo(left, axisBottom)
                    ctx.lineTo(width - right, axisBottom)
                    ctx.stroke()

                    ctx.strokeStyle = Theme.AppTheme.textMuted
                    ctx.lineWidth = 1
                    for (let tick = 0; tick < root.lineAxisTicks.length; tick += 1) {
                        const y = yFor(root.lineAxisTicks[tick])
                        ctx.beginPath()
                        ctx.moveTo(left - 4, y)
                        ctx.lineTo(left, y)
                        ctx.stroke()
                    }
                    for (let index = 0; index < rows.length; index += 1) {
                        const x = xFor(index)
                        ctx.beginPath()
                        ctx.moveTo(x, axisBottom)
                        ctx.lineTo(x, axisBottom + 4)
                        ctx.stroke()
                    }

                    const hasTarget = rows.some(function(point) {
                        return point.targetValue !== undefined && point.targetValue !== null
                    })
                    if (hasTarget) {
                        if (ctx.setLineDash) {
                            ctx.setLineDash([5, 4])
                        }
                        ctx.strokeStyle = Theme.AppTheme.textMuted
                        ctx.lineWidth = 1.5
                        ctx.beginPath()
                        for (let index = 0; index < rows.length; index += 1) {
                            const point = rows[index]
                            const x = xFor(index)
                            const y = yFor(point.targetValue || 0)
                            if (index === 0) {
                                ctx.moveTo(x, y)
                            } else {
                                ctx.lineTo(x, y)
                            }
                        }
                        ctx.stroke()
                        if (ctx.setLineDash) {
                            ctx.setLineDash([])
                        }
                    }

                    ctx.strokeStyle = Theme.AppTheme.accent
                    ctx.lineWidth = 3
                    ctx.beginPath()
                    for (let index = 0; index < rows.length; index += 1) {
                        const point = rows[index]
                        const x = xFor(index)
                        const y = yFor(point.value || 0)
                        if (index === 0) {
                            ctx.moveTo(x, y)
                        } else {
                            ctx.lineTo(x, y)
                        }
                    }
                    ctx.stroke()

                    ctx.fillStyle = Theme.AppTheme.accent
                    for (let index = 0; index < rows.length; index += 1) {
                        const point = rows[index]
                        const x = xFor(index)
                        const y = yFor(point.value || 0)
                        ctx.beginPath()
                        ctx.arc(x, y, 4, 0, Math.PI * 2)
                        ctx.fill()
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 0
            visible: root.chartType === "line" && (root.points || []).length > 0
            spacing: Theme.AppTheme.spacingXs

            Item {
                Layout.preferredWidth: 48
            }

            Repeater {
                model: root.points || []

                delegate: Label {
                    required property var modelData
                    Layout.fillWidth: true
                    text: String(modelData.label || modelData.supportingText || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 2
            visible: root.chartType === "line" && (root.points || []).length > 0
            spacing: Theme.AppTheme.spacingMd

            RowLayout {
                spacing: Theme.AppTheme.spacingXs

                Rectangle {
                    implicitWidth: 12
                    implicitHeight: 3
                    radius: 2
                    color: Theme.AppTheme.accent
                }

                Label {
                    text: "Actual"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }
            }

            RowLayout {
                visible: (root.points || []).some(function(point) {
                    return point.targetValue !== undefined && point.targetValue !== null
                })
                spacing: Theme.AppTheme.spacingXs

                Rectangle {
                    implicitWidth: 12
                    implicitHeight: 3
                    radius: 2
                    color: Theme.AppTheme.textMuted
                }

                Label {
                    text: "Target"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                }
            }

            Item {
                Layout.fillWidth: true
            }
        }

        ScrollView {
            id: barChartScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 132
            implicitHeight: 180
            visible: root.chartType !== "line" && (root.points || []).length > 0
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: barChartScroll.availableWidth > 0 ? barChartScroll.availableWidth : barChartScroll.width
                spacing: Theme.AppTheme.spacingSm

                Repeater {
                    model: root.points || []

                    delegate: ColumnLayout {
                        id: barDelegate

                        required property var modelData

                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingSm

                            Label {
                                Layout.fillWidth: true
                                text: barDelegate.modelData.label || ""
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }

                            Label {
                                text: barDelegate.modelData.valueLabel || ""
                                color: root.toneColor(barDelegate.modelData.tone)
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 10
                            radius: 5
                            color: Theme.AppTheme.surfaceAlt

                            Rectangle {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                width: Math.max(
                                    6,
                                    Math.min(
                                        parent.width,
                                        (Number(barDelegate.modelData.value || 0) / Math.max(root.maxValue, 1)) * parent.width
                                    )
                                )
                                radius: parent.radius
                                color: root.toneColor(barDelegate.modelData.tone)
                            }
                        }

                        Label {
                            Layout.fillWidth: true
                            visible: String(barDelegate.modelData.supportingText || "").length > 0
                            text: barDelegate.modelData.supportingText || ""
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }
}
