from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


VIEWPORTS = (
    (1024, 640),
    (1280, 720),
    (1366, 768),
    (1440, 900),
    (1920, 1080),
)
DIALOGS = ("ForecastGenerationDialog", "ForecastLifecycleDialog")
DIALOG_ROOT = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/financials/dialogs"
).resolve()


def _application() -> QGuiApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QGuiApplication.instance() or QGuiApplication(["r6c-forecast-qml"])


@pytest.mark.parametrize(("width", "height"), VIEWPORTS)
@pytest.mark.parametrize("dialog_type", DIALOGS)
def test_forecast_dialogs_fit_supported_viewports_and_keep_actions_reachable(
    width: int, height: int, dialog_type: str
) -> None:
    app = _application()
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    dialog_url = (DIALOG_ROOT / f"{dialog_type}.qml").as_uri()
    component.setData(
        dedent(
            f"""
            import QtQuick
            import QtQuick.Controls

            ApplicationWindow {{
                width: {width}
                height: {height}
                visible: true
                readonly property var forecastDialog: dialogLoader.item

                Loader {{
                    id: dialogLoader
                    source: "{dialog_url}"
                    onLoaded: item.open()
                }}
            }}
            """
        ).encode("utf-8"),
        f"r6c-{dialog_type}-{width}x{height}.qml",
    )

    root = component.create()
    assert root is not None, "\n".join(error.toString() for error in component.errors())
    app.processEvents()

    dialog = root.property("forecastDialog")
    assert dialog is not None
    assert 0 < float(dialog.property("width")) <= width
    assert 0 < float(dialog.property("height")) <= height
    assert float(dialog.property("x")) >= 0
    assert float(dialog.property("y")) >= 0

    cancel = dialog.findChild(QObject, "dialogCancelButton")
    submit = dialog.findChild(QObject, "dialogSubmitButton")
    assert cancel is not None and bool(cancel.property("visible"))
    assert submit is not None and bool(submit.property("visible"))
    assert bool(dialog.property("focus"))

    QTest.keyClick(root, Qt.Key_Escape)
    app.processEvents()
    assert not bool(dialog.property("visible"))

    root.deleteLater()
    app.processEvents()
