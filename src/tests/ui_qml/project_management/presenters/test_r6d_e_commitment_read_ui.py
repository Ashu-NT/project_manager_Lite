from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickItem

from src.ui_qml.shell.qml_engine import create_qml_engine


SECTION = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/financials/sections/FinancialsCommitmentsSection.qml"
).resolve()


@pytest.mark.parametrize("width", (700, 900, 1024, 1280, 1440))
def test_commitment_filter_stays_within_read_only_section(qapp, width):
    engine = create_qml_engine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(SECTION)))
    assert component.isReady(), component.errors()
    section = component.create()
    assert isinstance(section, QQuickItem), component.errors()
    try:
        section.setWidth(width)
        qapp.processEvents()
        filter_control = section.findChild(QQuickItem, "financialsCommitmentExposureFilter")
        assert filter_control is not None
        position = filter_control.mapToItem(section, QPointF(0, 0))
        assert position.x() >= 0
        assert position.x() + filter_control.width() <= width
        assert filter_control.isEnabled()
    finally:
        section.deleteLater()
        engine.deleteLater()
