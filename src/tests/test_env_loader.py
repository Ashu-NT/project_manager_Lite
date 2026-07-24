from __future__ import annotations

import os

from src.infra.platform.env_loader import load_env_file


def test_load_env_file_sets_missing_values(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "# comment",
                "PM_THEME=dark",
                "export PM_SKIP_LOGIN=1",
                "PM_SUPPORT_EMAIL='support@example.com'",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("PM_THEME", raising=False)
    monkeypatch.delenv("PM_SKIP_LOGIN", raising=False)
    monkeypatch.delenv("PM_SUPPORT_EMAIL", raising=False)

    loaded_path = load_env_file(env_path)

    assert loaded_path == env_path
    assert os.getenv("PM_THEME") == "dark"
    assert os.getenv("PM_SKIP_LOGIN") == "1"
    assert os.getenv("PM_SUPPORT_EMAIL") == "support@example.com"


def test_load_env_file_does_not_override_existing_values(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("PM_THEME=dark\n", encoding="utf-8")
    monkeypatch.setenv("PM_THEME", "light")

    load_env_file(env_path)

    assert os.getenv("PM_THEME") == "light"
