import pytest
from PySide6.QtCore import QPointF, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


@pytest.mark.parametrize("width,height", [(1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)])
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("rate,expected", [("null", "Not applicable"), ("0", "0.0%")])
def test_commitment_availability_visible_at_supported_viewports(qapp, width, height, theme, rate, expected):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(f'''
        import QtQuick
        import QtQuick.Controls
        import App.Theme 1.0 as Theme
        import workspaces.financials.commitments.sections 1.0
        ApplicationWindow {{
            width: {width}; height: {height}; visible: true
            Component.onCompleted: Theme.AppTheme.themeMode = "{theme}"
            FinancialsCommitmentsSection {{
                objectName: "commitments"
                width: parent.width - 340
                height: parent.height
                commitmentSummaryModel: ({{
                    approvedBudgetLabel: "USD 0.00", postedActualLabel: "USD 0.00",
                    openCommitmentLabel: "USD 0.00", availableAfterCommitmentLabel: "USD 0.00",
                    commitmentRatePct: {rate}
                }})
            }}
        }}
    '''.encode(), QUrl("r6h-commitment.qml"))
    window = component.create()
    assert window is not None, [error.toString() for error in component.errors()]
    try:
        QTest.qWait(50)
        section = window.findChild(QQuickItem, "commitments")

        def descendants(item):
            yield item
            for child in item.childItems():
                yield from descendants(child)

        label = next(item for item in descendants(section) if item.property("text") == expected)
        position = label.mapToItem(section, QPointF(0, 0))
        assert label.isVisible()
        assert position.y() + label.height() <= height
        assert label.property("contentWidth") <= label.width() + 1
        assert 0 <= position.x() <= section.width() - label.width() + 1
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
