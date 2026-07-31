"""Verify an ADR-003 authorization-transition evidence manifest offline."""

# RBAC-TRANSITION-ONLY: Remove the CLI after final promotion and retention.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.infra.security import (
    AuthorizationTransitionEvidenceError,
    verify_authorization_transition_evidence,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate ADR-003 backup, rehearsal, retention, approval, inventory, "
            "and policy artifacts without connecting to or changing a database."
        )
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to the external authorization-transition evidence manifest.",
    )
    parser.add_argument(
        "--expected-environment",
        help="Fail if the manifest names a different deployment environment ID.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional immutable JSON verification receipt path.",
    )
    return parser


def _write_receipt(path: Path, payload: dict[str, object]) -> Path:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return resolved


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = verify_authorization_transition_evidence(
            args.manifest,
            expected_environment_id=args.expected_environment,
        )
        if args.output is not None:
            receipt_path = _write_receipt(args.output, result)
            result = {**result, "verification_receipt": str(receipt_path)}
    except (AuthorizationTransitionEvidenceError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
