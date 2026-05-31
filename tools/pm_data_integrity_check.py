"""CLI: report Project Management data-integrity problems.

Read-only. Connects to the configured application database, runs every PM
integrity check, and prints a report. Exits non-zero if any ERROR-severity
finding is present (useful for CI / pre-migration gating).

    python -m tools.pm_data_integrity_check
"""

from __future__ import annotations

import sys

from src.core.modules.project_management.infrastructure.persistence.health import (
    run_pm_data_integrity_checks,
)
from src.infra.persistence.db.session_factory import SessionLocal


def main() -> int:
    session = SessionLocal()
    try:
        report = run_pm_data_integrity_checks(session)
    finally:
        session.close()

    for line in report.to_lines():
        print(line)

    has_errors = any(f.severity == "error" for f in report.problems)
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
