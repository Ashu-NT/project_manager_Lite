from __future__ import annotations

import json
from zipfile import ZipFile

from infra.diagnostics import build_diagnostics_bundle
from infra.update import check_for_updates


def test_check_for_updates_detects_newer_release_from_manifest_file(tmp_path):
    manifest = {
        "channels": {
            "stable": {
                "version": "2.2.0",
                "url": "https://example.com/download.exe",
                "notes": "Release notes",
                "sha256": "abc123",
            }
        }
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = check_for_updates(
        current_version="2.1.0",
        channel="stable",
        manifest_source=str(manifest_path),
    )

    assert result.update_available is True
    assert result.latest is not None
    assert result.latest.version == "2.2.0"
    assert "Update available" in result.message


def test_diagnostics_bundle_includes_metadata(tmp_path):
    out_path = tmp_path / "diag.zip"
    result = build_diagnostics_bundle(
        output_path=out_path,
        settings_snapshot={"update_channel": "stable"},
        include_db_copy=False,
    )

    assert result.output_path == out_path
    assert out_path.exists()
    with ZipFile(out_path) as bundle:
        names = set(bundle.namelist())
    assert "metadata.json" in names
