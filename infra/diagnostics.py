from __future__ import annotations

import json
import platform
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from infra.operational_support import redact_value
from infra.path import default_db_path, user_data_dir
from infra.version import get_app_version


@dataclass(frozen=True)
class DiagnosticsBundleResult:
    output_path: Path
    files_added: int
    warnings: tuple[str, ...]


def build_diagnostics_bundle(
    output_path: str | Path,
    *,
    settings_snapshot: dict[str, object] | None = None,
    include_db_copy: bool = True,
    incident_id: str | None = None,
) -> DiagnosticsBundleResult:
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []

    with TemporaryDirectory(prefix="pm_diag_") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        logs_dir = user_data_dir() / "logs"
        db_path = default_db_path()
        normalized_incident = (incident_id or "").strip()

        metadata = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "app_version": get_app_version(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "db_path": str(db_path),
            "logs_dir": str(logs_dir),
            "incident_id": normalized_incident or None,
            "settings": redact_value(settings_snapshot or {}),
        }
        (temp_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        copied_any_log = False
        support_events_path: Path | None = None
        if logs_dir.exists():
            for log_file in logs_dir.glob("app.log*"):
                if not log_file.is_file():
                    continue
                copied_any_log = True
                shutil.copy2(log_file, temp_dir / log_file.name)
            candidate_support_events = logs_dir / "support-events.jsonl"
            if candidate_support_events.exists() and candidate_support_events.is_file():
                copied_any_log = True
                support_events_path = candidate_support_events
                shutil.copy2(candidate_support_events, temp_dir / candidate_support_events.name)
        if not copied_any_log:
            warnings.append("No application logs were found.")

        if normalized_incident:
            incident_file_name = _incident_trace_filename(normalized_incident)
            incident_events = _load_incident_events(
                support_events_path=support_events_path,
                incident_id=normalized_incident,
            )
            if incident_events:
                (temp_dir / incident_file_name).write_text(
                    json.dumps(incident_events, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
            else:
                warnings.append(
                    f"No structured support events were found for incident '{normalized_incident}'."
                )

        if include_db_copy:
            if db_path.exists() and db_path.is_file():
                shutil.copy2(db_path, temp_dir / db_path.name)
            else:
                warnings.append("Database file not found; skipped DB snapshot.")

        files_added = 0
        with ZipFile(out_path, mode="w", compression=ZIP_DEFLATED) as bundle:
            for file_path in temp_dir.iterdir():
                if not file_path.is_file():
                    continue
                bundle.write(file_path, arcname=file_path.name)
                files_added += 1

    return DiagnosticsBundleResult(
        output_path=out_path,
        files_added=files_added,
        warnings=tuple(warnings),
    )


def _incident_trace_filename(incident_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in incident_id.strip())
    safe = safe.strip("_") or "unknown"
    return f"incident_trace_{safe}.json"


def _load_incident_events(
    *,
    support_events_path: Path | None,
    incident_id: str,
) -> list[dict[str, object]]:
    if support_events_path is None or not support_events_path.exists():
        return []
    wanted = incident_id.strip()
    if not wanted:
        return []

    results: list[dict[str, object]] = []
    for line in support_events_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        row = line.strip()
        if not row:
            continue
        try:
            payload = json.loads(row)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("trace_id") or "").strip() != wanted:
            continue
        results.append(redact_value(payload))
    return results


__all__ = ["DiagnosticsBundleResult", "build_diagnostics_bundle"]
