import QtQuick
import App.Theme 1.0 as Theme

Text {
    id: icon

    property string name: "default"
    property color iconColor: Theme.AppTheme.textSecondary
    property int size: 16

    readonly property var _map: ({
        "add":           "",
        "admin":         "",
        "approve":       "",
        "assets":        "",
        "calendar":      "",
        "catalog":       "",
        "close":         "",
        "collaboration": "",
        "control":       "",
        "dashboard":     "",
        "default":       "",
        "delete":        "",
        "edit":          "",
        "export":        "",
        "filter":        "",
        "financials":    "",
        "history":       "",
        "home":          "",
        "import":        "",
        "inventory":     "",
        "maintenance":   "",
        "notifications": "",
        "planner":       "",
        "portfolio":     "",
        "pricing":       "",
        "procurement":   "",
        "project":       "",
        "refresh":       "",
        "register":      "",
        "reject":        "",
        "reliability":   "",
        "reservations":  "",
        "resources":     "",
        "risk":          "",
        "search":        "",
        "settings":      "",
        "tasks":         "",
        "timesheets":    "",
        "user":          "",
        "workflow":      ""
    })

    text: icon._map[icon.name] !== undefined ? icon._map[icon.name] : icon._map["default"]
    color: icon.iconColor
    font.family: "Segoe MDL2 Assets"
    font.pixelSize: icon.size
    renderType: Text.NativeRendering
}