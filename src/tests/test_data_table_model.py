from src.ui_qml.shared.models.data_table_model import DynamicTableModel


def test_dynamic_table_model_skips_reset_for_identical_rows_and_columns() -> None:
    model = DynamicTableModel()
    resets: list[str] = []
    row_events: list[str] = []
    column_events: list[str] = []

    model.modelReset.connect(lambda: resets.append("reset"))
    model.rowsChanged.connect(lambda: row_events.append("rows"))
    model.columnsChanged.connect(lambda: column_events.append("columns"))

    rows = [
        {"id": "task-1", "title": "Cable Pull", "statusLabel": "In Progress"},
        {"id": "task-2", "title": "Commissioning", "statusLabel": "Todo"},
    ]
    columns = [
        {"key": "title", "label": "Task", "visible": True},
        {"key": "statusLabel", "label": "Status", "visible": True},
    ]

    model.rows = rows
    model.columns = columns

    assert resets == ["reset", "reset"]
    assert row_events == ["rows"]
    assert column_events == ["columns"]

    model.rows = list(rows)
    model.columns = [dict(column) for column in columns]

    assert resets == ["reset", "reset"]
    assert row_events == ["rows"]
    assert column_events == ["columns"]

    model.rows = rows + [{"id": "task-3", "title": "Closeout", "statusLabel": "Done"}]

    assert resets == ["reset", "reset", "reset"]
    assert row_events == ["rows", "rows"]

