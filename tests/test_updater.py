from __future__ import annotations

import infra.updater as updater


def test_download_update_installer_from_file_url(tmp_path):
    payload = b"installer-binary"
    source = tmp_path / "Setup_ProjectManagerLite_9.9.9.exe"
    source.write_bytes(payload)
    downloads = tmp_path / "downloads"

    path = updater.download_update_installer(
        url=source.as_uri(),
        download_dir=downloads,
        timeout_seconds=5,
    )

    assert path.exists()
    assert path.read_bytes() == payload


def test_verify_sha256_matches_payload(tmp_path):
    target = tmp_path / "installer.exe"
    target.write_bytes(b"abc123")
    digest = updater.sha256_file(target)

    assert updater.verify_sha256(target, digest) is True
    assert updater.verify_sha256(target, "deadbeef") is False


def test_prepare_windows_update_handoff_writes_script(monkeypatch, tmp_path):
    monkeypatch.setattr(updater.os, "name", "nt")
    installer = tmp_path / "Setup_ProjectManagerLite_2.1.2.exe"
    installer.write_bytes(b"payload")
    output = tmp_path / "updates"

    prepared = updater.prepare_windows_update_handoff(
        installer_path=installer,
        app_pid=1234,
        relaunch_executable=r"C:\Program Files\App\ProjectManagerLite.exe",
        relaunch_args=[],
        output_dir=output,
    )

    script_text = prepared.script_path.read_text(encoding="utf-8")
    assert "Get-Process -Id $targetPid" in script_text
    assert "Start-Process -FilePath $installer -Wait -PassThru" in script_text
    assert "Start-Process -FilePath $relaunchExe" in script_text
