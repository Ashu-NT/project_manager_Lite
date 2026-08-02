"""Create a read-only tenancy/RBAC migration inventory artifact."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sqlalchemy import create_engine

from src.infra.platform.env_loader import load_env_file
from src.infra.security import build_tenancy_rbac_inventory


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect tenancy and authorization data without applying migrations "
            "or changing authority."
        )
    )
    parser.add_argument(
        "--database-url",
        help="Database URL. Defaults to PM_DB_URL or the configured desktop database.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON artifact path. Existing files are not overwritten.",
    )
    parser.add_argument(
        "--fail-on",
        choices=("never", "critical", "high", "any"),
        default="never",
        help="Optional CI exit threshold. Default: never.",
    )
    return parser


def _database_url(explicit_url: str | None) -> str:
    if str(explicit_url or "").strip():
        return str(explicit_url).strip()
    configured = str(os.getenv("PM_DB_URL") or "").strip()
    if configured:
        return configured
    from src.infra.platform.path import default_db_path

    return f"sqlite:///{default_db_path().as_posix()}"


def _write_artifact(path: Path, payload: dict[str, object]) -> Path:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return resolved


def _should_fail(report: dict[str, object], threshold: str) -> bool:
    if threshold == "never":
        return False
    snapshot = report.get("snapshot")
    counts = (
        snapshot.get("finding_counts_by_severity", {})
        if isinstance(snapshot, dict)
        else {}
    )
    if not isinstance(counts, dict):
        return False
    if threshold == "critical":
        return int(counts.get("critical", 0) or 0) > 0
    if threshold == "high":
        return any(
            int(counts.get(severity, 0) or 0) > 0
            for severity in ("critical", "high")
        )
    return any(int(value or 0) > 0 for value in counts.values())


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    args = _build_parser().parse_args(argv)
    engine = create_engine(_database_url(args.database_url), future=True)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                if connection.dialect.name == "sqlite":
                    connection.exec_driver_sql("PRAGMA query_only = ON")
                elif connection.dialect.name == "postgresql":
                    connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                report = build_tenancy_rbac_inventory(connection)
            finally:
                transaction.rollback()
    finally:
        engine.dispose()

    if args.output is not None:
        artifact_path = _write_artifact(args.output, report)
        print(
            json.dumps(
                {
                    "artifact": str(artifact_path),
                    "snapshot_sha256": report["snapshot_sha256"],
                    "finding_counts_by_severity": report["snapshot"][
                        "finding_counts_by_severity"
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if _should_fail(report, args.fail_on) else 0


if __name__ == "__main__":
    raise SystemExit(main())
