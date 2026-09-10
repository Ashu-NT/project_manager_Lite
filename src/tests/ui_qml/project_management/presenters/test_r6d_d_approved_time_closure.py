from __future__ import annotations

import inspect
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent

from src.core.modules.project_management.application.financials.cost.entries.approved_time_consumer import (
    ApprovedTimeLaborCostConsumer,
)
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
    ProjectCostEntryService,
)
from src.core.modules.project_management.api.desktop.financials.models.cost_entries import (
    FinancialPostingFailurePageDto,
)
from src.infra.integration.approved_time_dispatcher import ApprovedTimeFinancialDispatcher
from src.ui_qml.modules.project_management.presenters.financials.destination_builder import (
    build_destination_state,
)
from src.ui_qml.shell.qml_engine import create_qml_engine


SECTION = Path(
    "src/ui_qml/modules/project_management/qml/workspaces/financials/sections/FinancialsPostingFailuresSection.qml"
).resolve()


def test_presenter_maps_table_roles_to_semantic_server_sort_keys() -> None:
    desktop_api = MagicMock()
    desktop_api.list_approved_time_posting_failures.return_value = (
        FinancialPostingFailurePageDto(
            sort_key="source",
            sort_direction="asc",
        )
    )

    state = build_destination_state(
        desktop_api,
        destination="costs",
        subsection="posting_failures",
        selected_project_id="project-1",
        posting_failure_sort_key="title",
        posting_failure_sort_direction="asc",
    )

    desktop_api.list_approved_time_posting_failures.assert_called_once_with(
        "project-1",
        page=1,
        page_size=50,
        sort_key="source",
        sort_direction="asc",
        status="",
    )
    assert state.posting_failure_sort_key == "title"
    assert state.posting_failure_sort_direction == "asc"


def test_posting_failure_surface_is_server_owned_bounded_and_read_only(qapp) -> None:
    engine = create_qml_engine()
    component = QQmlComponent(engine)
    component.setData(
        dedent(
            f"""
            import QtQuick
            import QtQuick.Controls

            ApplicationWindow {{
                width: 1024
                height: 640
                visible: true
                ListModel {{
                    id: failureRows
                    ListElement {{
                        rowId: "receipt-1"
                        title: "Time source-1 | revision 1"
                        statusLabel: "Retry"
                        subtitle: "Rate configuration | RATE_CARD_NO_APPLICABLE_RATE"
                        supportingText: "Configure an applicable cost rate"
                        metaText: "2026-05-13"
                    }}
                }}
                Loader {{
                    anchors.fill: parent
                    source: "{SECTION.as_uri()}"
                    onLoaded: {{
                        item.failuresModel = {{
                            "items": [{{"id": "receipt-1"}}],
                            "page": 1,
                            "pageSize": 1,
                            "total": 2
                        }}
                        item.failuresTableModel = failureRows
                    }}
                }}
            }}
            """
        ).encode("utf-8"),
        QUrl("r6dd-posting-failures.qml"),
    )
    window = component.create()
    assert window is not None, "\n".join(
        error.toString() for error in component.errors()
    )
    try:
        qapp.processEvents()
        table = window.findChild(QObject, "financialsPostingFailuresTable")
        pagination = window.findChild(QObject, "financialsPostingFailuresPagination")
        status_filter = window.findChild(
            QObject,
            "financialsPostingFailureStatusFilter",
        )
        assert table is not None
        assert pagination is not None
        assert status_filter is not None
        assert table.property("sortingMode") == "server"
        assert bool(pagination.property("visible"))
        assert window.findChild(QObject, "postingFailureRetryButton") is None
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


def test_approved_time_flow_keeps_project_finance_out_of_accounting() -> None:
    sources = "\n".join(
        (
            inspect.getsource(ApprovedTimeLaborCostConsumer),
            inspect.getsource(ApprovedTimeFinancialDispatcher),
            inspect.getsource(ProjectCostEntryService.apply_approved_time_source),
        )
    ).lower()
    for forbidden in (
        "accounting",
        "journal_entry",
        "general_ledger",
        "payable",
        "payroll",
        "invoice",
        "integration:project_finance",
        "hourly_rate",
        "cost_entries_changed",
    ):
        assert forbidden not in sources
