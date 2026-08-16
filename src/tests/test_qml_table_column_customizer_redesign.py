"""Redesign of the DataTable column customizer: a centered, modal two-pane
dialog (App.Widgets.TableColumnCustomizer) replacing the old toolbar-
anchored popup with move-left/move-right row buttons.

LEFT pane = visibility (checkbox + name, order fixed to the current draft
order). RIGHT pane = order (drag-and-drop reorder of visible/active
columns; hidden columns render dimmed in their slot and cannot themselves
be dragged, but an active column can be dragged across/around them). Both
panes are views onto one shared `_draft` array, so toggling a column's
visibility never touches its array position -- re-enabling a hidden column
trivially "retains its current position" because nothing moved it.

Rather than simulate pixel-perfect mouse drags against a dialog whose
on-screen position/size are runtime-computed (CenteredDialog centers on
the window and sizes to content), this exercises the exact same functions
the real MouseArea/CheckBox/button handlers call (`_setVisible`,
`_dragPress`/`_dragMoveTo`/`_dragRelease`, `_apply`/`_cancel`) -- see the
"named function, thin caller" refactor in TableColumnCustomizer.qml."""

from __future__ import annotations

from textwrap import dedent

from PySide6.QtCore import Qt, qInstallMessageHandler
from PySide6.QtQml import QJSValue, QQmlComponent
from PySide6.QtTest import QTest

from src.ui_qml.shell.qml_engine import create_qml_engine


def _create_harness(qapp, source: str):
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(dedent(source).encode("utf-8"), "table-column-customizer-test.qml")
    root = component.create()
    assert root is not None, "\n".join(error.toString() for error in component.errors())
    qapp.processEvents()
    return engine, component, root


def _to_py(value):
    return value.toVariant() if isinstance(value, QJSValue) else value


def _harness_source(window_width=900, window_height=700, with_nonconfigurable=False):
    extra_column = (
        ',{key: "id", label: "ID", visible: true, configurable: false}'
        if with_nonconfigurable
        else ""
    )
    return f"""
    import QtQuick
    import App.Widgets 1.0 as AppWidgets

    Window {{
        id: harness
        width: {window_width}
        height: {window_height}
        visible: true
        property var currentColumns: [
            {{key: "a", label: "Alpha", visible: true, visibleByDefault: true, configurable: true}},
            {{key: "b", label: "Bravo", visible: true, visibleByDefault: true, configurable: true}},
            {{key: "c", label: "Charlie", visible: false, visibleByDefault: true, configurable: true}},
            {{key: "d", label: "Delta", visible: true, visibleByDefault: false, configurable: true}}
            {extra_column}
        ]
        property var appliedColumns: null
        property int applyCount: 0
        property var customizerRef: customizer

        AppWidgets.TableColumnCustomizer {{
            id: customizer
            columns: harness.currentColumns
            onColumnVisibilityChanged: function(cols) {{
                harness.appliedColumns = cols
                harness.applyCount += 1
                harness.currentColumns = cols
            }}
        }}
    }}
    """


def test_initial_draft_reflects_committed_state_and_excludes_nonconfigurable(qapp) -> None:
    engine, component, root = _create_harness(qapp, _harness_source(with_nonconfigurable=True))
    customizer = root.property("customizerRef")

    customizer.open()
    qapp.processEvents()

    draft = _to_py(customizer.property("_draft"))
    assert [d["key"] for d in draft] == ["a", "b", "c", "d"], (
        "non-configurable columns must not appear in either pane"
    )
    assert [d["visible"] for d in draft] == [True, True, False, True]

    customizer.close()
    root.deleteLater()
    del component, engine


def test_set_visible_is_the_single_source_of_truth_for_both_panes(qapp) -> None:
    engine, component, root = _create_harness(qapp, _harness_source())
    customizer = root.property("customizerRef")

    customizer.open()
    qapp.processEvents()

    customizer._setVisible(2, True)
    draft = _to_py(customizer.property("_draft"))
    assert draft[2]["key"] == "c"
    assert draft[2]["visible"] is True, (
        "left pane's checkbox toggle must update the exact array the right "
        "pane also renders from -- there is no separate order-pane state"
    )

    customizer._setVisible(0, False)
    draft = _to_py(customizer.property("_draft"))
    assert draft[0]["visible"] is False

    customizer.close()
    root.deleteLater()
    del component, engine


def test_hidden_rows_cannot_be_dragged_but_active_rows_cross_them_freely(qapp) -> None:
    engine, component, root = _create_harness(qapp, _harness_source())
    customizer = root.property("customizerRef")

    customizer.open()
    qapp.processEvents()

    # index 2 ("c") starts hidden -- pressing its grip must not start a drag.
    started = customizer._dragPress(2)
    assert _to_py(started) is False
    assert _to_py(customizer.property("_draggingIndex")) == -1

    # index 0 ("a") is visible -- starts a drag, and can be dropped past the
    # hidden "c" row into the last slot.
    started = customizer._dragPress(0)
    assert _to_py(started) is True
    assert _to_py(customizer.property("_draggingIndex")) == 0

    customizer._dragMoveTo(3)
    draft = _to_py(customizer.property("_draft"))
    assert [d["key"] for d in draft] == ["b", "c", "d", "a"]
    assert _to_py(customizer.property("_draggingIndex")) == 3

    customizer._dragRelease()
    assert _to_py(customizer.property("_draggingIndex")) == -1

    customizer.close()
    root.deleteLater()
    del component, engine


def test_reenabling_a_hidden_column_retains_its_current_position(qapp) -> None:
    engine, component, root = _create_harness(qapp, _harness_source())
    customizer = root.property("customizerRef")

    customizer.open()
    qapp.processEvents()

    # Move "a" past the hidden "c" row: [a,b,c,d] -> [b,c,d,a]
    customizer._dragPress(0)
    customizer._dragMoveTo(3)
    customizer._dragRelease()
    draft = _to_py(customizer.property("_draft"))
    assert [d["key"] for d in draft] == ["b", "c", "d", "a"]

    # Re-enable "c" (now sitting at index 1) via the visibility pane -- it
    # must stay at index 1, not jump anywhere.
    customizer._setVisible(1, True)
    draft = _to_py(customizer.property("_draft"))
    assert [d["key"] for d in draft] == ["b", "c", "d", "a"]
    assert draft[1]["visible"] is True

    customizer.close()
    root.deleteLater()
    del component, engine


def test_cancel_discards_and_apply_commits_then_reopen_reflects_it(qapp) -> None:
    engine, component, root = _create_harness(qapp, _harness_source())
    customizer = root.property("customizerRef")

    # --- Cancel path: mutate, then cancel -- nothing should be committed.
    customizer.open()
    qapp.processEvents()
    customizer._setVisible(0, False)
    customizer._dragPress(1)
    customizer._dragMoveTo(3)
    customizer._dragRelease()
    customizer._cancel()
    qapp.processEvents()

    assert _to_py(root.property("applyCount")) == 0

    customizer.open()
    qapp.processEvents()
    draft = _to_py(customizer.property("_draft"))
    assert [d["key"] for d in draft] == ["a", "b", "c", "d"], (
        "reopening after Cancel must reflect the still-committed original "
        "configuration, not the discarded in-progress edits"
    )
    assert draft[0]["visible"] is True

    # --- Apply path: mutate, then apply -- both visibility and order commit.
    customizer._setVisible(2, True)
    customizer._dragPress(3)
    customizer._dragMoveTo(0)
    customizer._dragRelease()
    customizer._apply()
    qapp.processEvents()

    assert _to_py(root.property("applyCount")) == 1
    applied = _to_py(root.property("appliedColumns"))
    assert [c["key"] for c in applied] == ["d", "a", "b", "c"]
    assert applied[3]["visible"] is True

    # Reopening now must reflect the just-committed configuration.
    customizer.open()
    qapp.processEvents()
    draft = _to_py(customizer.property("_draft"))
    assert [d["key"] for d in draft] == ["d", "a", "b", "c"]
    assert draft[3]["visible"] is True

    customizer.close()
    root.deleteLater()
    del component, engine


def test_dialog_stays_within_a_compact_window(qapp) -> None:
    engine, component, root = _create_harness(
        qapp, _harness_source(window_width=480, window_height=360)
    )
    customizer = root.property("customizerRef")

    customizer.open()
    qapp.processEvents()

    dialog_width = _to_py(customizer.property("width"))
    dialog_height = _to_py(customizer.property("height"))
    dialog_x = _to_py(customizer.property("x"))
    dialog_y = _to_py(customizer.property("y"))

    assert dialog_width <= 480
    assert dialog_height <= 360
    assert dialog_x >= 0
    assert dialog_y >= 0
    assert dialog_x + dialog_width <= 480 + 1  # +1 rounding slack
    assert dialog_y + dialog_height <= 360 + 1

    customizer.close()
    root.deleteLater()
    del component, engine


def test_escape_closes_without_committing(qapp) -> None:
    engine, component, root = _create_harness(qapp, _harness_source())
    customizer = root.property("customizerRef")

    customizer.open()
    qapp.processEvents()
    customizer._setVisible(0, False)

    QTest.keyClick(root, Qt.Key.Key_Escape)
    qapp.processEvents()

    assert _to_py(customizer.property("visible")) is False
    assert _to_py(root.property("applyCount")) == 0

    root.deleteLater()
    del component, engine


def test_data_table_open_column_customizer_call_path_has_no_qml_warnings(qapp) -> None:
    # Regression: DataTable.openColumnCustomizer(anchorItem) used to also
    # assign the (now-removed) `anchorItem` property on the customizer
    # instance to position the old anchored popup. After the redesign to a
    # centered dialog that property no longer exists, and a stale
    # `_colCustomizer.anchorItem = ...` assignment left behind in
    # DataTable.qml's openColumnCustomizer() silently logged
    # "Cannot assign to non-existent property "anchorItem"" on every open
    # instead of raising -- this exercises the exact real call path (through
    # DataTable, not the customizer directly) and fails loudly on any such
    # QML warning.
    messages = []
    previous_handler = qInstallMessageHandler(
        lambda mode, context, message: messages.append(message)
    )
    try:
        engine, component, root = _create_harness(
            qapp,
            """
            import QtQuick
            import QtQuick.Controls
            import App.Widgets 1.0 as AppWidgets

            Window {
                id: harness
                width: 900
                height: 700
                visible: true

                Button {
                    id: customizeButton
                    text: "Customize"
                }

                AppWidgets.DataTable {
                    id: table
                    anchors.fill: parent
                    columns: [
                        {key: "a", label: "Alpha", flex: 0, minWidth: 100},
                        {key: "b", label: "Bravo", flex: 0, minWidth: 100}
                    ]
                    rows: [{id: "1", a: "x", b: "y"}]
                }

                Component.onCompleted: table.openColumnCustomizer(customizeButton)
            }
            """,
        )
        qapp.processEvents()

        assert not any("anchorItem" in message for message in messages), (
            f"openColumnCustomizer() logged a QML warning about anchorItem: {messages}"
        )
        assert not any("non-existent property" in message for message in messages), (
            f"openColumnCustomizer() logged an unexpected QML property warning: {messages}"
        )

        root.deleteLater()
        del component, engine
    finally:
        qInstallMessageHandler(previous_handler)
