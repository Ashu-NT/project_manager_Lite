from __future__ import annotations

from infra import version as version_mod


def test_get_app_version_prefers_env_override(monkeypatch, tmp_path):
    version_file = tmp_path / "app_version.txt"
    version_file.write_text("2.1.1", encoding="utf-8")
    monkeypatch.setattr(version_mod, "_VERSION_FILE", version_file)
    monkeypatch.setenv("PM_APP_VERSION", "9.9.9")

    assert version_mod.get_app_version() == "9.9.9"


def test_get_app_version_reads_runtime_version_file(monkeypatch, tmp_path):
    version_file = tmp_path / "app_version.txt"
    version_file.write_text("2.1.1", encoding="utf-8")
    monkeypatch.setattr(version_mod, "_VERSION_FILE", version_file)
    monkeypatch.delenv("PM_APP_VERSION", raising=False)

    assert version_mod.get_app_version() == "2.1.1"


def test_get_app_version_falls_back_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(version_mod, "_VERSION_FILE", tmp_path / "missing.txt")
    monkeypatch.delenv("PM_APP_VERSION", raising=False)

    assert version_mod.get_app_version() == version_mod._DEFAULT_APP_VERSION
