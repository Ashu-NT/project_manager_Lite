from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickWindow

from src.ui_qml.shell.qml_engine import create_qml_engine


ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PAGE = ROOT / "ui_qml/platform/qml/settings/SettingsWorkspacePage.qml"
PLATFORM_WORKSPACE = ROOT / "ui_qml/platform/qml/workspace/PlatformWorkspace.qml"
RELEASE_PANEL = (
    ROOT / "ui_qml/platform/qml/support/sections/AdminSupportReleasePanel.qml"
)


@pytest.mark.parametrize("source", [SETTINGS_PAGE, PLATFORM_WORKSPACE])
def test_platform_settings_loads_without_runtime_binding_warnings(
    qapp, source: Path
) -> None:
    messages: list[str] = []

    def capture_message(_message_type, _context, message: str) -> None:
        messages.append(str(message))

    previous_handler = qInstallMessageHandler(capture_message)
    page = None
    window = None
    try:
        engine = create_qml_engine()
        component = QQmlComponent(
            engine,
            QUrl.fromLocalFile(str(source.resolve())),
        )
        page = component.create()
        assert page is not None, "\n".join(
            error.toString() for error in component.errors()
        )

        window = QQuickWindow()
        window.resize(1280, 720)
        page.setParentItem(window.contentItem())
        page.setWidth(1280)
        page.setHeight(720)
        if source == PLATFORM_WORKSPACE:
            page.setProperty("activeDestination", "settings")
        window.show()
        qapp.processEvents()

        relevant = [
            message
            for message in messages
            if "ReferenceError" in message or "Cannot find member data" in message
        ]
        assert not relevant, "\n".join(relevant)
    finally:
        if page is not None:
            page.setParentItem(None)
            page.deleteLater()
        if window is not None:
            window.close()
            window.deleteLater()
        qapp.processEvents()
        qInstallMessageHandler(previous_handler)


def test_release_panel_owns_controller_state_synchronization(qapp) -> None:
    engine = create_qml_engine()
    component = QQmlComponent(
        engine,
        QUrl.fromLocalFile(str(RELEASE_PANEL.resolve())),
    )
    panel = component.create()
    assert panel is not None, "\n".join(
        error.toString() for error in component.errors()
    )

    try:
        panel.setProperty(
            "supportSettings",
            {
                "updateChannel": "beta",
                "updateAutoCheck": True,
                "updateManifestSource": "https://example.test/manifest.json",
                "channelOptions": [
                    {"label": "Stable", "value": "stable"},
                    {"label": "Beta", "value": "beta"},
                ],
            },
        )
        qapp.processEvents()

        channel = panel.findChild(QObject, "supportUpdateChannelCombo")
        auto_check = panel.findChild(QObject, "supportAutoCheckBox")
        manifest = panel.findChild(QObject, "supportManifestField")
        assert channel is not None
        assert auto_check is not None
        assert manifest is not None
        assert channel.property("currentIndex") == 1
        assert auto_check.property("checked") is True
        assert manifest.property("text") == "https://example.test/manifest.json"
    finally:
        panel.deleteLater()
        qapp.processEvents()
