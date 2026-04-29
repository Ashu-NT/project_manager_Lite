from __future__ import annotations

import json

from PySide6.QtCore import QSettings

import src.api.desktop.platform.support as support_module
import src.infra.platform.diagnostics as diagnostics_module
from src.api.desktop.platform import (
    PlatformSupportDesktopApi,
    SupportSettingsUpdateCommand,
)
from src.infra.platform.operational_support import OperationalSupport


def _settings(tmp_path):
    settings = QSettings(str(tmp_path / "support_settings.ini"), QSettings.IniFormat)
    settings.clear()
    settings.sync()
    return settings


def test_platform_support_desktop_api_persists_settings_and_checks_updates(tmp_path):
    manifest_path = tmp_path / "release-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "channels": {
                    "stable": {
                        "version": "9.9.9",
                        "url": "https://example.com/downloads/pm-9.9.9.exe",
                        "notes": "Modern QML admin support.",
                        "sha256": "deadbeef",
                    },
                    "beta": {
                        "version": "10.0.0-beta1",
                        "url": "https://example.com/downloads/pm-10.0.0-beta1.exe",
                        "notes": "Preview release",
                        "sha256": "cafebabe",
                    },
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    operational_support = OperationalSupport(events_path=tmp_path / "logs" / "support-events.jsonl")
    api = PlatformSupportDesktopApi(
        settings=_settings(tmp_path),
        operational_support=operational_support,
    )
    command = SupportSettingsUpdateCommand(
        update_channel="beta",
        update_auto_check=True,
        update_manifest_source=str(manifest_path),
    )

    save_result = api.save_settings(command, trace_id="inc-support-1")
    check_result = api.check_for_updates(command, trace_id="inc-support-1")
    activity_result = api.list_activity(trace_id="inc-support-1")

    assert save_result.ok is True
    assert save_result.data is not None
    assert save_result.data.update_channel == "beta"
    assert save_result.data.update_auto_check is True
    assert save_result.data.update_manifest_source == str(manifest_path)

    assert check_result.ok is True
    assert check_result.data is not None
    assert check_result.data.status_label == "Update Available"
    assert check_result.data.channel == "beta"
    assert check_result.data.update_available is True
    assert check_result.data.latest_version == "10.0.0-beta1"
    assert check_result.data.can_open_download is True
    assert check_result.data.download_url.endswith("pm-10.0.0-beta1.exe")

    assert activity_result.ok is True
    assert activity_result.data is not None
    assert activity_result.data[0].event_type == "support.update.available"
    assert any(row.event_type == "support.update.settings_saved" for row in activity_result.data)


def test_platform_support_desktop_api_builds_diagnostics_and_incident_packages(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "app.log").write_text("application-log", encoding="utf-8")

    operational_support = OperationalSupport(events_path=logs_dir / "support-events.jsonl")
    operational_support.emit_event(
        event_type="support.test",
        message="Support workflow started.",
        trace_id="inc-support-2",
    )

    monkeypatch.setattr(support_module, "user_data_dir", lambda: data_dir)
    monkeypatch.setattr(diagnostics_module, "user_data_dir", lambda: data_dir)
    monkeypatch.setattr(diagnostics_module, "default_db_path", lambda: data_dir / "project_manager.db")

    api = PlatformSupportDesktopApi(
        settings=_settings(tmp_path),
        operational_support=operational_support,
    )

    diagnostics_result = api.export_diagnostics(incident_id="inc-support-2")
    incident_result = api.create_incident_report(incident_id="inc-support-2")
    paths_result = api.get_paths()
    activity_result = api.list_activity(trace_id="inc-support-2")

    assert diagnostics_result.ok is True
    assert diagnostics_result.data is not None
    assert diagnostics_result.data.output_path.endswith(".zip")
    assert "pm_diagnostics_" in diagnostics_result.data.output_path
    assert diagnostics_result.data.files_added >= 2

    assert incident_result.ok is True
    assert incident_result.data is not None
    assert "pm_incident_inc-support-2_" in incident_result.data.output_path
    assert incident_result.data.support_email == "tech_ash_673@info.tech"

    assert paths_result.ok is True
    assert paths_result.data is not None
    assert paths_result.data.logs_directory_path == str(logs_dir)
    assert paths_result.data.data_directory_path == str(data_dir)

    assert activity_result.ok is True
    assert activity_result.data is not None
    assert activity_result.data[0].event_type == "support.incident.report_ready"
    assert any(row.event_type == "support.diagnostics.exported" for row in activity_result.data)
