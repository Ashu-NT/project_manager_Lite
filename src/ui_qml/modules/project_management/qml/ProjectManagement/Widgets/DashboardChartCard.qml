pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    property string chartType: "bar"
    property string emptyState: ""
    property var points: []

    readonly property real maxValue: root.computeMaxValue()

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

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitWidth: 420
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    onPointsChanged: lineCanvas.requestPaint()
    onWidthChanged: lineCanvas.requestPaint()
    onHeightChanged: lineCanvas.requestPaint()

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
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

        Canvas {
            id: lineCanvas

            Layout.fillWidth: true
            visible: root.chartType === "line" && (root.points || []).length > 0
            implicitHeight: 220

            onPaint: {
                const ctx = getContext("2d")
                const rows = root.points || []
                ctx.reset()
                ctx.clearRect(0, 0, width, height)
                if (!rows.length) {
                    return
                }

                const left = 18
                const right = 18
                const top = 18
                const bottom = 28
                const plotWidth = Math.max(1, width - left - right)
                const plotHeight = Math.max(1, height - top - bottom)
                const denominator = Math.max(rows.length - 1, 1)
                const maxValue = Math.max(root.maxValue, 1)

                function xFor(index) {
                    return left + (plotWidth * index / denominator)
                }

                function yFor(value) {
                    return top + plotHeight - ((Number(value || 0) / maxValue) * plotHeight)
                }

                ctx.strokeStyle = Theme.AppTheme.border
                ctx.lineWidth = 1
                for (let grid = 0; grid < 3; grid += 1) {
                    const y = top + (plotHeight * grid / 2)
                    ctx.beginPath()
                    ctx.moveTo(left, y)
                    ctx.lineTo(width - right, y)
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

        RowLayout {
            Layout.fillWidth: true
            visible: root.chartType === "line" && (root.points || []).length > 0
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: (root.points || []).length > 0 ? ((root.points || [])[0].supportingText || (root.points || [])[0].label || "") : ""
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
            }

            Label {
                text: (root.points || []).length > 0 ? ((root.points || [])[(root.points || []).length - 1].supportingText || (root.points || [])[(root.points || []).length - 1].label || "") : ""
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                horizontalAlignment: Text.AlignRight
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root.chartType !== "line" && (root.points || []).length > 0
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
                        border.color: Theme.AppTheme.border

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
