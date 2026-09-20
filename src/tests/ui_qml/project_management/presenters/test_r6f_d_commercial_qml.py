from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


@pytest.mark.parametrize(
    "width,height", [(1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)]
)
def test_commercial_section_preserves_zero_and_availability_at_viewports(
    qapp, width, height
):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        f"""
        import QtQuick
        import QtQuick.Controls
        import workspaces.financials.revenue.sections 1.0
        ApplicationWindow {{
            width: {width}; height: {height}; visible: true
            FinancialsCommercialProjectionSection {{
                objectName: "commercialSection"
                width: parent.width
                projection: ({{fields: [
                    {{label: "Zero revenue", value: 0}},
                    {{label: "Zero margin", value: "0.00"}},
                    {{label: "No cost authority", value: "Canonical EAC unavailable"}},
                    {{label: "Permission", value: "Restricted"}},
                    {{label: "Unsupported", value: "Projection unavailable for this billing method"}},
                    {{label: "Zero denominator", value: "Not applicable"}}
                ]}})
            }}
        }}
    """.encode(),
        QUrl("r6fd-commercial.qml"),
    )
    window = component.create()
    assert window is not None, [error.toString() for error in component.errors()]
    try:
        QTest.qWait(100)
        qapp.processEvents()
        section = window.findChild(QObject, "commercialSection")

        def visual_items(item):
            yield item
            for child in item.childItems():
                yield from visual_items(child)

        assert isinstance(section, QQuickItem)
        texts = [obj.property("text") for obj in visual_items(section)]
        for value in (
            "0",
            "0.00",
            "Canonical EAC unavailable",
            "Restricted",
            "Projection unavailable for this billing method",
            "Not applicable",
        ):
            assert value in texts
        assert section.property("width") == width
        assert section.property("implicitHeight") <= height
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
