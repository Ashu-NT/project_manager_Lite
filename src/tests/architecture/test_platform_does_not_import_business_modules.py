"""ADR-005 Sec21 (Architecture Guardrails): Platform must not depend on a concrete business
module's implementation, except through explicitly governed, cited exceptions.

Uses the same AST-based technique already proven in this test suite (see
test_qml_architecture_guardrails_layers.py, test_pm_inventory_module_boundary.py) -- no new
enforcement framework is introduced.

Scope note (documentation/implementation mismatch found and corrected while implementing this
test): ADR-005 Sec21's prose says the guardrail scans "src/core/platform/{domain,application}/",
but Sec22 says the SqlAlchemyApprovalRepository -> ProjectORM violation (which lives under
src/core/platform/infrastructure/) is allowlisted "in the new guardrail test". Those two
statements are inconsistent -- a domain/application-only scan would never see the
infrastructure-layer violation Sec22 says this test allowlists. This test scans the whole
src/core/platform/ tree, matching Sec22's actual intent and the audit's own methodology (which
found both known violations by grepping all of src/core/platform/, not a narrower subtree).
ADR-005 Sec21's wording has been corrected to match (see the ADR's own revision note).
"""

from __future__ import annotations

import ast
from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT

PLATFORM_ROOT = REPO_ROOT / "src" / "core" / "platform"
FORBIDDEN_PACKAGE = "src.core.modules"

# Any new entry here requires a citation to an accepted ADR in the same change -- an
# uncited addition fails review, not just this test.
GOVERNED_EXCEPTIONS: dict[str, str] = {
    "src/core/platform/application/time_management/calendar/assignment/calendar_assignment_service.py": (
        "ADR-004: Calendar Assignment Split Ownership."
    ),
    "src/core/platform/infrastructure/persistence/repositories/approval/approval.py": (
        "ADR-005 Sec22: pre-existing, separately tracked architectural debt -- "
        "SqlAlchemyApprovalRepository imports ProjectORM directly; no project-scoping "
        "contract exists yet. Classified as debt that may remain, not a blocker, and not "
        "to be silently fixed as a side effect of the domain-event migration. DO NOT add a "
        "new exception to this dict without an equivalent governing citation."
    ),
}


def _python_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _business_module_import_hits(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source, filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == FORBIDDEN_PACKAGE or node.module.startswith(f"{FORBIDDEN_PACKAGE}."):
                hits.append(f"{node.lineno} imports {node.module}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == FORBIDDEN_PACKAGE or alias.name.startswith(f"{FORBIDDEN_PACKAGE}."):
                    hits.append(f"{node.lineno} imports {alias.name}")
    return hits


def _scan_platform(*, exceptions: frozenset[str]) -> list[str]:
    violations: list[str] = []
    for path in _python_files(PLATFORM_ROOT):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in exceptions:
            continue
        for hit in _business_module_import_hits(path):
            violations.append(f"{relative}:{hit}")
    return violations


def test_platform_core_does_not_import_business_modules() -> None:
    violations = _scan_platform(exceptions=frozenset(GOVERNED_EXCEPTIONS))

    assert not violations, (
        "Platform imports a concrete business module without a governing ADR citation "
        "(ADR-005 Sec21). Add an entry to GOVERNED_EXCEPTIONS only with an accepted ADR "
        "citation in the same change:\n" + "\n".join(violations)
    )


def test_governed_exceptions_are_exactly_the_two_known_violations() -> None:
    """Guards the allowlist itself against silent growth or shrinkage -- any change to this
    set must be a deliberate, reviewed edit, not an incidental one."""
    assert set(GOVERNED_EXCEPTIONS) == {
        "src/core/platform/application/time_management/calendar/assignment/calendar_assignment_service.py",
        "src/core/platform/infrastructure/persistence/repositories/approval/approval.py",
    }


def test_guardrail_detects_violations_when_exceptions_are_not_applied() -> None:
    """Proves the scanner has teeth: with the allowlist emptied, it must still find (at
    least) the two known, currently-exempted violations. If this ever finds nothing, the
    scanner itself is broken -- the codebase did not suddenly become clean."""
    violations = _scan_platform(exceptions=frozenset())

    assert violations, "Expected the unexempted scan to find known violations; found none."
    assert any("calendar_assignment_service.py" in v for v in violations), violations
    assert any(
        "infrastructure/persistence/repositories/approval/approval.py" in v for v in violations
    ), violations
