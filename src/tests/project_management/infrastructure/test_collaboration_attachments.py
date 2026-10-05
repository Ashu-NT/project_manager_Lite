from __future__ import annotations

from pathlib import Path

import pytest

from src.core.modules.project_management.infrastructure import collaboration_attachments


def test_same_name_sources_have_distinct_physical_identity(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(collaboration_attachments, "user_data_dir", lambda: tmp_path / "data")
    first = tmp_path / "first" / "evidence.txt"
    second = tmp_path / "second" / "evidence.txt"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("first")
    second.write_text("second")

    paths = collaboration_attachments.store_task_comment_attachments(
        task_id="task-1", comment_id="comment-1", attachments=[str(first), str(second)]
    )

    assert len(set(paths)) == 2
    assert [Path(path).name for path in paths] == ["evidence.txt", "evidence.txt"]
    assert [Path(path).read_text() for path in paths] == ["first", "second"]
    collaboration_attachments.cleanup_task_comment_attachments(paths)
    assert all(not Path(path).exists() for path in paths)


def test_missing_source_fails_before_any_copy(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(collaboration_attachments, "user_data_dir", lambda: tmp_path / "data")
    existing = tmp_path / "existing.txt"
    existing.write_text("valid")

    with pytest.raises(FileNotFoundError):
        collaboration_attachments.store_task_comment_attachments(
            task_id="task-1", comment_id="comment-1",
            attachments=[str(existing), str(tmp_path / "missing.txt")],
        )

    assert not (tmp_path / "data" / "collaboration" / "attachments").exists()


def test_copy_failure_cleans_staged_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(collaboration_attachments, "user_data_dir", lambda: tmp_path / "data")
    source = tmp_path / "evidence.txt"
    source.write_text("valid")

    def fail_copy(_source, target):
        Path(target).write_text("partial")
        raise OSError("copy failed")

    monkeypatch.setattr(collaboration_attachments, "copy2", fail_copy)
    with pytest.raises(OSError, match="copy failed"):
        collaboration_attachments.store_task_comment_attachments(
            task_id="task-1", comment_id="comment-1", attachments=[str(source)]
        )

    assert list((tmp_path / "data" / "collaboration" / "attachments").rglob("*.txt")) == []


def test_cleanup_refuses_unmanaged_path(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(collaboration_attachments, "user_data_dir", lambda: tmp_path / "data")
    external = tmp_path / "external.txt"
    external.write_text("keep")

    with pytest.raises(ValueError, match="outside managed storage"):
        collaboration_attachments.cleanup_task_comment_attachments([str(external)])

    assert external.read_text() == "keep"
