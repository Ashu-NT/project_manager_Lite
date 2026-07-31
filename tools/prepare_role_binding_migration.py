"""Build, review, or persist a legacy role-binding migration preparation."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.infra.platform.env_loader import load_env_file


# RBAC-TRANSITION-ONLY: Remove after canonical backfill, rollback closure, and
# migration-evidence archival. This command cannot apply canonical authority.
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or persist reviewed legacy role-binding migration evidence."
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        help="Read-only tenancy/RBAC inventory artifact used for preview or review.",
    )
    parser.add_argument(
        "--review",
        type=Path,
        help="Security-review decisions; produces an immutable reviewed plan.",
    )
    parser.add_argument(
        "--plan",
        type=Path,
        help="Reviewed plan artifact used only with --apply.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Exclusive preview or reviewed-plan artifact path.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist preparation evidence only; does not create role bindings.",
    )
    parser.add_argument(
        "--expected-hash",
        help="Exact reviewed plan SHA-256 required with --apply.",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        help="Exclusive preparation receipt path required with --apply.",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("PM_ROLE_BINDING_MIGRATION_USERNAME", "admin"),
        help="Platform operator username used only with --apply.",
    )
    parser.add_argument(
        "--mfa-code",
        default=os.getenv("PM_ROLE_BINDING_MIGRATION_MFA_CODE"),
        help="Optional current MFA code used only with --apply.",
    )
    return parser


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.apply:
        if args.plan is None:
            parser.error("--plan is required with --apply")
        if not str(args.expected_hash or "").strip():
            parser.error("--expected-hash is required with --apply")
        if args.receipt is None:
            parser.error("--receipt is required with --apply")
        if any(value is not None for value in (args.inventory, args.review, args.output)):
            parser.error(
                "--apply accepts --plan, --expected-hash, and --receipt; "
                "inventory/review/output belong to offline stages"
            )
        return

    if args.inventory is None:
        parser.error("--inventory is required for offline preview/review")
    if args.output is None:
        parser.error("--output is required for offline preview/review")
    if any(value is not None for value in (args.plan, args.receipt, args.expected_hash)):
        parser.error("--plan, --receipt, and --expected-hash require --apply")


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"Invalid JSON artifact '{path}'.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Artifact '{path}' must contain one JSON object.")
    return payload


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return resolved


def _require_absent(path: Path | None, parser: argparse.ArgumentParser) -> None:
    if path is not None and path.expanduser().resolve().exists():
        parser.error(f"artifact already exists: {path}")


def _resolve_password() -> str:
    configured = os.getenv("PM_ROLE_BINDING_MIGRATION_PASSWORD")
    if configured is not None and configured.strip():
        return configured.strip()
    if not sys.stdin.isatty():
        raise RuntimeError(
            "PM_ROLE_BINDING_MIGRATION_PASSWORD must be set for non-interactive use."
        )
    return getpass.getpass("Platform operator password: ")


def _offline_stage(args: argparse.Namespace) -> dict[str, object]:
    from src.infra.security.role_binding_migration_plan import (
        build_reviewed_role_binding_migration_plan,
        build_role_binding_migration_preview,
        load_role_binding_migration_review,
    )

    inventory = _read_json(args.inventory)
    preview = build_role_binding_migration_preview(inventory)
    if args.review is None:
        return preview.model_dump(mode="json")
    review = load_role_binding_migration_review(args.review)
    plan = build_reviewed_role_binding_migration_plan(preview, review)
    return plan.model_dump(mode="json")


def _apply_stage(args: argparse.Namespace) -> dict[str, object]:
    from src.core.platform.auth import AuthService
    from src.core.platform.auth.domain import UserSessionContext
    from src.infra.composition.repositories import build_repository_bundle
    from src.infra.persistence.db.session_factory import SessionLocal
    from src.infra.platform.logging_config import setup_logging
    from src.infra.security.role_binding_migration_plan import (
        load_reviewed_role_binding_migration_plan,
    )
    from src.infra.security.role_binding_migration_preparation import (
        RoleBindingMigrationPreparationService,
    )
    from src.infra.security.tenancy_rbac_inventory import (
        build_tenancy_rbac_inventory,
    )

    setup_logging()
    plan = load_reviewed_role_binding_migration_plan(args.plan)
    password = _resolve_password()
    session = SessionLocal()
    try:
        repositories = build_repository_bundle(session)
        user_session = UserSessionContext()
        auth_service = AuthService(
            session=session,
            user_repo=repositories.user_repo,
            role_repo=repositories.role_repo,
            permission_repo=repositories.permission_repo,
            user_role_repo=repositories.user_role_repo,
            role_permission_repo=repositories.role_permission_repo,
            auth_session_repo=repositories.auth_session_repo,
            scoped_access_repo=repositories.scoped_access_repo,
            project_membership_repo=repositories.project_membership_repo,
            user_session=user_session,
            user_tenant_repo=repositories.user_tenant_repo,
            role_binding_repo=repositories.role_binding_repo,
        )
        actor = auth_service.authenticate(
            args.username,
            password,
            mfa_code=args.mfa_code,
            device_label="role-binding-migration-preparation",
        )
        user_session.set_principal(auth_service.build_principal(actor))
        service = RoleBindingMigrationPreparationService(
            session=session,
            migration_repo=repositories.role_binding_migration_repo,
            audit_repo=repositories.audit_entry_repo,
            user_session=user_session,
            current_inventory_provider=lambda: build_tenancy_rbac_inventory(
                session.connection()
            ),
        )
        result = service.prepare(
            plan,
            expected_plan_sha256=args.expected_hash,
        )
        return {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "operation": "authorization.migration.prepared",
            "batch_id": result.batch.id,
            "source_inventory_sha256": result.batch.source_inventory_sha256,
            "reviewed_plan_sha256": result.batch.reviewed_plan_sha256,
            "record_count": len(result.records),
            "ready_count": sum(record.status == "ready" for record in result.records),
            "quarantine_count": sum(
                record.status == "quarantined" for record in result.records
            ),
            "already_prepared": result.already_prepared,
        }
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    parser = _build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)
    _require_absent(args.receipt if args.apply else args.output, parser)

    payload = _apply_stage(args) if args.apply else _offline_stage(args)
    artifact_path = _write_json(
        args.receipt if args.apply else args.output,
        payload,
    )
    print(
        json.dumps(
            {
                "artifact": str(artifact_path),
                "mode": "prepare" if args.apply else (
                    "reviewed-plan" if args.review is not None else "preview"
                ),
                "sha256": payload.get("reviewed_plan_sha256")
                or payload.get("plan_sha256")
                or payload.get("preview_sha256"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
