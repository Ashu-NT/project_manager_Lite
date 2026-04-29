from __future__ import annotations

import json
from types import SimpleNamespace

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

    diagnostics_target = data_dir / "exports" / "chosen_diagnostics_bundle.zip"
    diagnostics_result = api.export_diagnostics_to(
        incident_id="inc-support-2",
        output_path=diagnostics_target.as_uri(),
    )
    incident_result = api.create_incident_report(incident_id="inc-support-2")
    paths_result = api.get_paths()
    activity_result = api.list_activity(trace_id="inc-support-2")

    assert diagnostics_result.ok is True
    assert diagnostics_result.data is not None
    assert diagnostics_result.data.output_path == str(diagnostics_target)
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


def test_platform_support_desktop_api_can_launch_windows_update_handoff(tmp_path, monkeypatch):
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
                    }
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    data_dir = tmp_path / "data"
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    operational_support = OperationalSupport(events_path=logs_dir / "support-events.jsonl")
    api = PlatformSupportDesktopApi(
        settings=_settings(tmp_path),
        operational_support=operational_support,
    )
    command = SupportSettingsUpdateCommand(
        update_channel="stable",
        update_auto_check=True,
        update_manifest_source=str(manifest_path),
    )
    installer_path = data_dir / "updates" / "pm-9.9.9.exe"
    installer_path.parent.mkdir(parents=True, exist_ok=True)
    installer_path.write_bytes(b"installer")
    handoff_script = data_dir / "updates" / "apply_update_test.ps1"
    handoff_script.write_text("Write-Host 'test'", encoding="utf-8")
    launched: dict[str, object] = {}

    monkeypatch.setattr(support_module, "user_data_dir", lambda: data_dir)
    monkeypatch.setattr(support_module.os, "name", "nt")
    monkeypatch.setattr(
        support_module,
        "download_update_installer",
        lambda *, url, download_dir: installer_path,
    )
    monkeypatch.setattr(support_module, "verify_sha256", lambda path, expected: True)
    monkeypatch.setattr(
        support_module,
        "prepare_windows_update_handoff",
        lambda **kwargs: SimpleNamespace(script_path=handoff_script, installer_path=installer_path),
    )
    monkeypatch.setattr(
        support_module,
        "launch_windows_update_handoff",
        lambda prepared: launched.setdefault("prepared", prepared),
    )

    result = api.install_available_update(command, trace_id="inc-support-3")
    activity_result = api.list_activity(trace_id="inc-support-3")

    assert result.ok is True
    assert result.data is not None
    assert result.data.latest_version == "9.9.9"
    assert result.data.installer_path == str(installer_path)
    assert result.data.handoff_script_path == str(handoff_script)
    assert launched["prepared"].installer_path == installer_path
    assert activity_result.ok is True
    assert activity_result.data is not None
    assert activity_result.data[0].event_type == "support.update.handoff_started"
