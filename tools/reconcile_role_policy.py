"""Preview or apply the managed system-role policy reconciliation."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.infra.platform.env_loader import load_env_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview or apply a reviewed system-role policy change-set."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the reviewed change-set. The default is dry-run.",
    )
    parser.add_argument(
        "--expected-version",
        type=int,
        help="Required with --apply; prior version reported by dry-run.",
    )
    parser.add_argument(
        "--expected-hash",
        help="Required with --apply; SHA-256 change-set hash reported by dry-run.",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("PM_POLICY_RECONCILE_USERNAME", "admin"),
        help="Platform operator username.",
    )
    parser.add_argument(
        "--mfa-code",
        default=os.getenv("PM_POLICY_RECONCILE_MFA_CODE"),
        help="Optional current MFA code.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional dry-run JSON output path.",
    )
    parser.add_argument(
        "--rollback-output",
        type=Path,
        help="Rollback artifact path. Required with --apply.",
    )
    return parser


def _resolve_password() -> str:
    configured = os.getenv("PM_POLICY_RECONCILE_PASSWORD")
    if configured is not None and configured.strip():
        return configured.strip()
    if not sys.stdin.isatty():
        raise RuntimeError(
            "PM_POLICY_RECONCILE_PASSWORD must be set for non-interactive use."
        )
    return getpass.getpass("Platform operator password: ")


def _plan_payload(plan) -> dict[str, object]:
    return {
        "policy_name": plan.policy_name,
        "current_version": plan.current_version,
        "target_version": plan.target_version,
        "change_set_hash": plan.change_set_hash,
        "has_changes": plan.has_changes,
        "additions": [
            {
                "role_name": change.role_name,
                "permission_code": change.permission_code,
            }
            for change in plan.additions
        ],
        "removals": [
            {
                "role_name": change.role_name,
                "permission_code": change.permission_code,
            }
            for change in plan.removals
        ],
        "affected_user_ids": list(plan.affected_user_ids),
        "active_session_ids": list(plan.active_session_ids),
        "missing_role_names": list(plan.missing_role_names),
        "missing_permission_codes": list(plan.missing_permission_codes),
        "rollback": json.loads(plan.rollback_json),
    }


def _write_json(
    path: Path,
    payload: dict[str, object],
    *,
    exclusive: bool = False,
) -> None:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("x" if exclusive else "w", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.apply and args.expected_version is None:
        parser.error("--expected-version is required with --apply")
    if args.apply and not str(args.expected_hash or "").strip():
        parser.error("--expected-hash is required with --apply")
    if args.apply and args.rollback_output is None:
        parser.error("--rollback-output is required with --apply")

    from src.core.platform.auth import AuthService
    from src.core.platform.auth.application import RolePolicyReconciliationService
    from src.core.platform.auth.domain import UserSessionContext
    from src.infra.composition.repositories import build_repository_bundle
    from src.infra.persistence.db.engine import get_db_url
    from src.infra.persistence.db.session_factory import SessionLocal
    from src.infra.persistence.migrations.runner import run_migrations
    from src.infra.platform.logging_config import setup_logging
    from src.infra.platform.security_config import (
        load_runtime_security_configuration,
    )

    setup_logging()
    load_runtime_security_configuration()
    password = _resolve_password()
    run_migrations(get_db_url())
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
        )
        actor = auth_service.authenticate(
            args.username,
            password,
            mfa_code=args.mfa_code,
            device_label="role-policy-reconciliation",
        )
        user_session.set_principal(auth_service.build_principal(actor))
        service = RolePolicyReconciliationService(
            session=session,
            role_repo=repositories.role_repo,
            permission_repo=repositories.permission_repo,
            role_permission_repo=repositories.role_permission_repo,
            user_role_repo=repositories.user_role_repo,
            user_repo=repositories.user_repo,
            auth_session_repo=repositories.auth_session_repo,
            reconciliation_repo=repositories.auth_policy_reconciliation_repo,
            user_session=user_session,
        )
        plan = service.preview()
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "apply" if args.apply else "dry-run",
            "plan": _plan_payload(plan),
        }
        if args.output is not None:
            _write_json(args.output, payload)
        if not args.apply:
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        rollback_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "reviewed_plan": _plan_payload(plan),
        }
        _write_json(args.rollback_output, rollback_payload, exclusive=True)
        result = service.apply(
            expected_version=args.expected_version,
            expected_change_set_hash=args.expected_hash,
        )
        print(
            json.dumps(
                {
                    "applied": result.applied,
                    "change_set_hash": result.plan.change_set_hash,
                    "from_version": result.plan.current_version,
                    "to_version": result.plan.target_version,
                    "revoked_session_count": result.revoked_session_count,
                    "rollback_artifact": str(
                        args.rollback_output.expanduser().resolve()
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
