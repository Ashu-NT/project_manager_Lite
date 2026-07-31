"""One-time platform-owner provisioning command.

Run from the repository root:

    python -m tools.provision_platform_owner
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from src.infra.platform.env_loader import load_env_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Provision the first platform owner exactly once."
    )
    parser.add_argument(
        "--username",
        default=os.getenv("PM_PLATFORM_OWNER_USERNAME", "admin"),
        help="Platform owner username. Defaults to PM_PLATFORM_OWNER_USERNAME or admin.",
    )
    parser.add_argument(
        "--display-name",
        default=os.getenv("PM_PLATFORM_OWNER_DISPLAY_NAME", "Platform Owner"),
        help="Human-readable platform owner name.",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("PM_PLATFORM_OWNER_EMAIL"),
        help="Optional platform owner email.",
    )
    return parser


def _resolve_password() -> str:
    configured = os.getenv("PM_PLATFORM_OWNER_PASSWORD")
    if configured is not None and configured.strip():
        return configured.strip()
    if not sys.stdin.isatty():
        raise RuntimeError(
            "PM_PLATFORM_OWNER_PASSWORD must be set for non-interactive provisioning."
        )
    first = getpass.getpass("Platform owner password: ")
    second = getpass.getpass("Confirm platform owner password: ")
    if first != second:
        raise RuntimeError("Platform owner passwords do not match.")
    return first


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    parser = _build_parser()
    args = parser.parse_args(argv)

    from src.core.platform.auth.application import AuthService
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
        auth_service = AuthService(
            session=session,
            user_repo=repositories.user_repo,
            role_repo=repositories.role_repo,
            permission_repo=repositories.permission_repo,
            role_permission_repo=repositories.role_permission_repo,
            auth_session_repo=repositories.auth_session_repo,
            scoped_access_repo=repositories.scoped_access_repo,
            project_membership_repo=repositories.project_membership_repo,
            user_tenant_repo=repositories.user_tenant_repo,
            role_binding_repo=repositories.role_binding_repo,
        )
        result = auth_service.provision_platform_owner(
            username=args.username,
            raw_password=password,
            audit_writer=repositories.audit_entry_repo,
            display_name=args.display_name,
            email=args.email,
            provisioning_actor=(
                os.getenv("PM_PROVISIONING_ACTOR")
                or getpass.getuser()
                or "deployment"
            ),
        )
    finally:
        session.close()

    state = "created" if result.created else "already provisioned"
    print(f"Platform owner {state}: username={result.username} user_id={result.user_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
