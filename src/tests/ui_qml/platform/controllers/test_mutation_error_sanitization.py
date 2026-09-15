from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError
from src.ui_qml.platform.controllers.common.error_sanitizer import (
    DEFAULT_SAFE_FAILURE_MESSAGE,
    safe_exception_message,
)
from src.ui_qml.platform.controllers.common.mutation_runner import run_mutation


class _RawInfrastructureError(Exception):
    """Stands in for sqlalchemy.exc.OperationalError and friends: a raw,
    non-domain exception whose text may contain SQL and bound parameters."""


def test_domain_error_message_passes_through_unchanged() -> None:
    exc = ValidationError("Site code must be unique.")
    assert safe_exception_message(exc) == "Site code must be unique."


def test_raw_infrastructure_error_is_sanitized() -> None:
    exc = _RawInfrastructureError(
        "(sqlite3.OperationalError) database is locked\n"
        "[SQL: INSERT INTO audit_entries ...]\n"
        "[parameters: ('6a561447-...', 'Test', ...)]"
    )
    message = safe_exception_message(exc)
    assert message == DEFAULT_SAFE_FAILURE_MESSAGE
    assert "SQL" not in message
    assert "sqlite3" not in message


def test_run_mutation_never_leaks_raw_exception_text_to_the_ui() -> None:
    captured: dict[str, object] = {"error": None, "operation_result": None, "busy": []}

    def _operation():
        raise _RawInfrastructureError(
            "(sqlite3.OperationalError) database is locked\n"
            "[SQL: INSERT INTO audit_entries (id, ...) VALUES (?, ?, ...)]\n"
            "[parameters: ('6a561447-4f5a-4c85-9d4a-791cd9b10496', 'Test', ...)]"
        )

    result = run_mutation(
        operation=_operation,
        success_message="Site created.",
        on_success=lambda: None,
        set_is_busy=lambda v: captured["busy"].append(v),
        set_error_message=lambda v: captured.__setitem__("error", v),
        set_operation_result=lambda v: captured.__setitem__("operation_result", v),
        set_feedback_message=lambda v: None,
    )

    assert result["ok"] is False
    assert "database is locked" not in str(captured["error"])
    assert "SQL" not in str(captured["error"])
    assert "INSERT INTO" not in str(captured["error"])
    assert captured["error"] == DEFAULT_SAFE_FAILURE_MESSAGE
    assert captured["operation_result"]["message"] == DEFAULT_SAFE_FAILURE_MESSAGE


def test_run_mutation_still_surfaces_curated_domain_messages() -> None:
    captured: dict[str, object] = {"error": None}

    def _operation():
        raise ValidationError("Site code SITE-2026-0001 is already in use.")

    run_mutation(
        operation=_operation,
        success_message="Site created.",
        on_success=lambda: None,
        set_is_busy=lambda v: None,
        set_error_message=lambda v: captured.__setitem__("error", v),
        set_operation_result=lambda v: None,
        set_feedback_message=lambda v: None,
    )

    assert captured["error"] == "Site code SITE-2026-0001 is already in use."
