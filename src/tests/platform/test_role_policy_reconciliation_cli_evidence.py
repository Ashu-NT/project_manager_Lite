from __future__ import annotations

# RBAC-TRANSITION-ONLY: Retire transition receipt assertions with the verifier;
# retain ordinary policy reconciliation coverage.

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import reconcile_role_policy


def test_policy_apply_requires_a_distinct_receipt_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rollback_path = tmp_path / "rollback.json"

    with pytest.raises(SystemExit) as exc_info:
        reconcile_role_policy.main(
            [
                "--apply",
                "--expected-version",
                "1",
                "--expected-hash",
                "a" * 64,
                "--rollback-output",
                str(rollback_path),
            ]
        )

    assert exc_info.value.code == 2
    assert "--output is required with --apply" in capsys.readouterr().err


def test_policy_apply_rejects_shared_receipt_and_rollback_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact_path = tmp_path / "shared.json"

    with pytest.raises(SystemExit) as exc_info:
        reconcile_role_policy.main(
            [
                "--apply",
                "--expected-version",
                "1",
                "--expected-hash",
                "a" * 64,
                "--output",
                str(artifact_path),
                "--rollback-output",
                str(artifact_path),
            ]
        )

    assert exc_info.value.code == 2
    assert "must be different paths" in capsys.readouterr().err


def test_policy_artifacts_are_exclusive_and_hashable(tmp_path: Path) -> None:
    artifact_path = tmp_path / "policy.json"
    payload = {"mode": "dry-run", "plan": {"change_set_hash": "a" * 64}}

    resolved = reconcile_role_policy._write_json(artifact_path, payload)

    assert json.loads(resolved.read_text(encoding="utf-8")) == payload
    assert len(reconcile_role_policy._sha256_file(resolved)) == 64
    with pytest.raises(FileExistsError):
        reconcile_role_policy._write_json(artifact_path, payload)


def test_apply_receipt_binds_result_to_rollback_digest(
    tmp_path: Path,
) -> None:
    rollback_path = tmp_path / "rollback.json"
    result = SimpleNamespace(
        applied=True,
        revoked_session_count=3,
        plan=SimpleNamespace(
            change_set_hash="a" * 64,
            current_version=1,
            target_version=2,
        ),
    )

    receipt = reconcile_role_policy._build_apply_receipt(
        {
            "schema_version": 1,
            "mode": "apply",
            "plan": {"change_set_hash": "a" * 64},
        },
        result,
        rollback_path=rollback_path,
        rollback_sha256="b" * 64,
    )

    assert receipt["mode"] == "apply"
    assert receipt["result"] == {
        "applied": True,
        "change_set_hash": "a" * 64,
        "from_version": 1,
        "to_version": 2,
        "revoked_session_count": 3,
        "rollback_artifact_reference": str(rollback_path),
        "rollback_artifact_sha256": "b" * 64,
    }
