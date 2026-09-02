from __future__ import annotations

from sqlalchemy.exc import OperationalError

from src.ui_qml.modules.project_management.controllers.financials.financials_mutation_mixin import (
    FinancialsMutationMixin,
)


class _Harness(FinancialsMutationMixin):
    def __init__(self) -> None:
        self.busy = False
        self.error_message = ""
        self.feedback_message = ""

    def _set_is_busy(self, value: bool) -> None:
        self.busy = value

    def _set_error_message(self, value: str) -> None:
        self.error_message = value

    def _set_feedback_message(self, value: str) -> None:
        self.feedback_message = value


def test_finance_mutation_does_not_expose_sql_or_parameters_to_qml() -> None:
    harness = _Harness()

    def _fail() -> None:
        raise OperationalError(
            "UPDATE secret_finance_table SET token=?",
            ("sensitive-value",),
            Exception("database is locked"),
        )

    result = harness._run_finance_mutation(_fail, "Saved.", lambda: None)

    assert result == {
        "ok": False,
        "message": (
            "The financial change could not be completed. Try again or refresh "
            "the workspace."
        ),
        "code": "FINANCE_MUTATION_FAILED",
        "category": "unexpected",
        "fieldErrors": {},
        "conflict": False,
    }
    assert harness.error_message == result["message"]
    assert "secret_finance_table" not in harness.error_message
    assert "sensitive-value" not in harness.error_message
    assert harness.busy is False
