from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import infra.diagnostics as diagnostics
from infra.operational_support import (
    REDACTED,
    REDACTED_EMAIL,
    OperationalSupport,
    bind_trace_id,
)


def test_operational_support_emits_redacted_structured_event(tmp_path):
    events_path = tmp_path / "support-events.jsonl"
    support = OperationalSupport(events_path=events_path)

    with bind_trace_id("inc-test-123"):
        trace_id = support.emit_event(
            event_type="support.test",
            message="token=abc123 alice@example.com",
            data={
                "password": "StrongPass123",
                "contact": "alice@example.com",
                "nested": {"api_token": "secret-value"},
            },
        )

    assert trace_id == "inc-test-123"
    rows = events_path.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    payload = json.loads(rows[0])
    assert payload["trace_id"] == "inc-test-123"
    assert payload["event_type"] == "support.test"
    assert "abc123" not in payload["message"]
    assert "alice@example.com" not in payload["message"]
    assert payload["data"]["password"] == REDACTED
    assert payload["data"]["nested"]["api_token"] == REDACTED
    assert payload["data"]["contact"] == REDACTED_EMAIL


def test_operational_support_capture_exception_records_crash_event(tmp_path):
    events_path = tmp_path / "support-events.jsonl"
    support = OperationalSupport(events_path=events_path)

    try:
        raise RuntimeError("token=bad-token")
    except RuntimeError as exc:
        support.capture_exception(
            exc_type=RuntimeError,
            exc_value=exc,
            exc_traceback=exc.__traceback__,
            context="unit-test",
            trace_id="inc-crash-1",
        )

    payload = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["event_type"] == "app.crash"
    assert payload["level"] == "ERROR"
    assert payload["trace_id"] == "inc-crash-1"
    assert "bad-token" not in payload["message"]
    assert payload["data"]["exception_type"] == "RuntimeError"


def test_diagnostics_bundle_includes_incident_trace_and_support_events(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "app.log").write_text("application-log", encoding="utf-8")

    events = [
        {
            "timestamp_utc": "2026-02-27T12:00:00+00:00",
            "event_type": "support.update.check_started",
            "level": "INFO",
            "trace_id": "inc-a",
            "message": "started",
        },
        {
            "timestamp_utc": "2026-02-27T12:00:10+00:00",
            "event_type": "support.update.available",
            "level": "INFO",
            "trace_id": "inc-b",
            "message": "available",
        },
    ]
    (logs_dir / "support-events.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in events),
        encoding="utf-8",
    )

    monkeypatch.setattr(diagnostics, "user_data_dir", lambda: data_dir)
    monkeypatch.setattr(diagnostics, "default_db_path", lambda: data_dir / "project_manager.db")

    out_path = tmp_path / "diagnostics.zip"
    result = diagnostics.build_diagnostics_bundle(
        output_path=out_path,
        settings_snapshot={"api_token": "raw-token", "contact_email": "alice@example.com"},
        include_db_copy=False,
        incident_id="inc-a",
    )

    assert result.output_path == out_path
    with ZipFile(out_path) as bundle:
        names = set(bundle.namelist())
        assert "metadata.json" in names
        assert "support-events.jsonl" in names
        assert "incident_trace_inc-a.json" in names
        metadata = json.loads(bundle.read("metadata.json").decode("utf-8"))
        trace_rows = json.loads(bundle.read("incident_trace_inc-a.json").decode("utf-8"))

    assert metadata["settings"]["api_token"] == REDACTED
    assert metadata["settings"]["contact_email"] == REDACTED_EMAIL
    assert len(trace_rows) == 1
    assert trace_rows[0]["trace_id"] == "inc-a"


def test_support_tab_wires_incident_tracing_and_operational_support():
    root = Path(__file__).resolve().parents[1]
    tab_text = (root / "ui" / "support" / "tab.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    telemetry_text = (root / "ui" / "support" / "telemetry.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    update_text = (root / "ui" / "support" / "update_flow.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    diagnostics_text = (root / "ui" / "support" / "diagnostics_flow.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )

    assert "SupportUiLayoutMixin" in tab_text
    assert "SupportTelemetryMixin" in tab_text
    assert "SupportUpdateFlowMixin" in tab_text
    assert "SupportDiagnosticsFlowMixin" in tab_text
    assert "get_operational_support()" in tab_text
    assert "def _current_incident_id" in telemetry_text
    assert "incident_id=incident_id" in update_text
    assert 'event_type="support.diagnostics.exported"' in diagnostics_text
