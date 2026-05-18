import QtQuick
import App.Theme 1.0 as Theme

Text {
    id: icon

    property string name: "default"
    property color iconColor: Theme.AppTheme.textSecondary
    property int size: 16

    readonly property var _map: ({
        "add": "",
        "admin": "",
        "approve": "",
        "close": "",
        "control": "",
        "default": "",
        "delete": "",
        "edit": "",
        "export": "",
        "filter": "",
        "history": "",
        "home": "",
        "import": "",
        "inventory": "",
        "maintenance": "",
        "notifications": "",
        "project": "",
        "refresh": "",
        "reject": "",
        "search": "",
        "settings": "",
        "user": "",
        "workflow": ""
    })

    text: icon._map[icon.name] !== undefined ? icon._map[icon.name] : icon._map["default"]
    color: icon.iconColor
    font.family: "Segoe MDL2 Assets"
    font.pixelSize: icon.size
    renderType: Text.NativeRendering
}
