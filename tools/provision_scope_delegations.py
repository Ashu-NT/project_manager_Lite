"""Preview or apply the reviewed resource-scope delegation catalog."""

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
        description="Preview or apply the reviewed scope-delegation catalog."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the reviewed change-set. The default is dry-run.",
    )
    parser.add_argument(
        "--expected-hash",
        help="Required with --apply; SHA-256 catalog hash reported by dry-run.",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("PM_SCOPE_DELEGATION_USERNAME", "admin"),
        help="Platform operator username.",
    )
    parser.add_argument(
        "--mfa-code",
        default=os.getenv("PM_SCOPE_DELEGATION_MFA_CODE"),
        help="Optional current MFA code.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional artifact path. Existing files are not overwritten.",
    )
    return parser


def _resolve_password() -> str:
    configured = os.getenv("PM_SCOPE_DELEGATION_PASSWORD")
    if configured is not None and configured.strip():
        return configured.strip()
    if not sys.stdin.isatty():
        raise RuntimeError(
            "PM_SCOPE_DELEGATION_PASSWORD must be set for non-interactive use."
        )
    return getpass.getpass("Platform operator password: ")


def _plan_payload(plan) -> dict[str, object]:
    return {
        "catalog_hash": plan.catalog_hash,
        "has_changes": plan.has_changes,
        "missing_role_names": sorted(plan.missing_role_names),
        "entries": [
            {
                "actor_role_name": entry.actor_role_name,
                "assignable_role_name": entry.assignable_role_name,
                "target_scope_type": entry.target_scope_type,
                "exists": entry.exists,
            }
            for entry in plan.entries
        ],
    }


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return resolved


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.apply and not str(args.expected_hash or "").strip():
        parser.error("--expected-hash is required with --apply")
    if (
        args.output is not None
        and args.output.expanduser().resolve().exists()
    ):
        parser.error(f"artifact already exists: {args.output}")

    from src.core.platform.auth import AuthService
    from src.core.platform.auth.application import (
        RoleGovernanceService,
        ScopeDelegationProvisioningService,
    )
    from src.core.platform.auth.domain import UserSessionContext
    from src.core.platform.tenancy import TenantContextService, build_tenant_context_policy
    from src.infra.composition.repositories import build_repository_bundle
    from src.infra.persistence.db.session_factory import SessionLocal
    from src.infra.platform.logging_config import setup_logging
    from src.infra.platform.security_config import load_runtime_security_configuration

    setup_logging()
    security_configuration = load_runtime_security_configuration()
    password = _resolve_password()
    session = SessionLocal()
    try:
        repositories = build_repository_bundle(session)
        user_session = UserSessionContext()
        tenant_context_service = TenantContextService(
            tenant_repo=repositories.tenant_repo,
            organization_repo=repositories.organization_repo,
            user_session=user_session,
            user_tenant_repo=repositories.user_tenant_repo,
            context_policy=build_tenant_context_policy(
                security_configuration.tenancy_mode
            ),
        )
        auth_service = AuthService(
            session=session,
            user_repo=repositories.user_repo,
            role_repo=repositories.role_repo,
            permission_repo=repositories.permission_repo,
            role_permission_repo=repositories.role_permission_repo,
            auth_session_repo=repositories.auth_session_repo,
            user_session=user_session,
            user_tenant_repo=repositories.user_tenant_repo,
            role_binding_repo=repositories.role_binding_repo,
            security_audit_repo=repositories.audit_entry_repo,
        )
        actor = auth_service.authenticate(
            args.username,
            password,
            mfa_code=args.mfa_code,
            device_label="scope-delegation-provisioning",
        )
        user_session.set_principal(auth_service.build_principal(actor))
        role_governance_service = RoleGovernanceService(
            session=session,
            role_repo=repositories.role_repo,
            role_binding_repo=repositories.role_binding_repo,
            delegation_repo=repositories.role_delegation_policy_repo,
            role_permission_repo=repositories.role_permission_repo,
            permission_repo=repositories.permission_repo,
            user_repo=repositories.user_repo,
            tenant_repo=repositories.tenant_repo,
            membership_repo=repositories.user_tenant_repo,
            audit_repo=repositories.audit_entry_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        )
        service = ScopeDelegationProvisioningService(
            role_repo=repositories.role_repo,
            delegation_repo=repositories.role_delegation_policy_repo,
            role_governance_service=role_governance_service,
        )
        plan = service.preview()
        payload = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "apply" if args.apply else "dry-run",
            "plan": _plan_payload(plan),
        }
        if not args.apply:
            if args.output is not None:
                _write_json(args.output, payload)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        result = service.apply(expected_catalog_hash=args.expected_hash)
        receipt = {
            **payload,
            "result": {
                "catalog_hash": result.catalog_hash,
                "created": [
                    {
                        "actor_role_name": entry.actor_role_name,
                        "assignable_role_name": entry.assignable_role_name,
                        "target_scope_type": entry.target_scope_type,
                    }
                    for entry in result.created
                ],
            },
        }
        if args.output is not None:
            _write_json(args.output, receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
