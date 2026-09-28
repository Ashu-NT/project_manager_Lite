import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


@pytest.mark.parametrize(
    "width,height", [(1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)]
)
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_accounting_collection_readable_and_plain_text(qapp, width, height, theme):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        f'''
        import QtQuick
        import QtQuick.Controls
        import App.Theme 1.0 as Theme
        import workspaces.financials.shared.sections 1.0
        ApplicationWindow {{
            width: {width}; height: {height}; visible: true
            Component.onCompleted: Theme.AppTheme.themeMode = "{theme}"
            ScrollView {{
                anchors.fill: parent
                FinancialsCollectionBlock {{
                    objectName: "statusCollection"
                    width: {width} - 340
                    collection: ({{title: "Accounting Handoffs & Outcomes", subtitle: "Delivery is not acknowledgement.",
                        total: 1, items: [{{id: "one", title: "BP-0001", statusLabel: "Acknowledged",
                        subtitle: "Transport: Transport delivered",
                        supportingText: "<b>Untrusted reference</b>\\n{'R' * 512}\\nAttempts: 0 of 5\\nQuarantined evidence: 1\\nManual retry is not supported.",
                        metaText: "2026-09-28T12:00:00+00:00"}}]}})
                }}
            }}
        }}
    '''.encode(),
        QUrl("r6ge-accounting.qml"),
    )
    window = component.create()
    assert window is not None, [error.toString() for error in component.errors()]
    try:
        QTest.qWait(100)
        qapp.processEvents()
        section = window.findChild(QObject, "statusCollection")
        assert isinstance(section, QQuickItem)

        def visual_items(item):
            yield item
            for child in item.childItems():
                yield from visual_items(child)

        texts = [
            item
            for item in visual_items(section)
            if isinstance(item.property("text"), str)
        ]
        supporting = next(
            item for item in texts if "Untrusted reference" in item.property("text")
        )
        expression = QQmlExpression(
            engine.rootContext(), supporting, "Number(textFormat)"
        )
        assert expression.evaluate()[0] == 0  # Text.PlainText
        assert "Attempts: 0 of 5" in supporting.property("text")
        for item in texts:
            assert item.width() >= 0
            if item.property("text"):
                assert item.property("contentWidth") <= section.width() + 1
        assert section.implicitHeight() < height
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
