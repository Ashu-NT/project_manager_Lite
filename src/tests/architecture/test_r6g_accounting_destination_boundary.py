"""The approved PM evidence contract must remain usable without a transport."""

import ast
from pathlib import Path

from sqlalchemy import UniqueConstraint

from src.core.modules.project_management.domain.financials.accounting.handoff import (
    AccountingHandoffSnapshot,
)
from src.core.modules.project_management.gateway.billing.accounting_billing import (
    ProjectBillingPreparationPayload,
)
from src.core.modules.project_management.infrastructure.persistence.orm.accounting.handoff import (
    ProjectAccountingHandoffORM,
    ProjectAccountingOutboxORM,
)

ROOT = Path(__file__).resolve().parents[3]


def test_canonical_handoff_has_no_external_runtime_dependency():
    pending = [
        "src.core.modules.project_management.domain.financials.accounting.handoff"
    ]
    seen = set()
    forbidden = (
        "src.infra",
        "src.application",
        "src.api",
        "src.core.platform.contract.port.integration.external_accounting",
        "src.core.platform.contract.port.integration.accounting_outcomes",
    )
    while pending:
        module = pending.pop()
        if module in seen:
            continue
        seen.add(module)
        assert not module.startswith(forbidden), module
        assert ".infrastructure" not in module and ".application" not in module, module
        path = ROOT / (module.replace(".", "/") + ".py")
        if not path.exists():
            path = ROOT / module.replace(".", "/") / "__init__.py"
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    base = (
                        module.split(".")
                        if path.name == "__init__.py"
                        else module.split(".")[:-1]
                    )
                    base = base[: len(base) - node.level + 1]
                    dependency = ".".join(base + ([node.module] if node.module else []))
                else:
                    dependency = node.module or ""
                if dependency.startswith("src."):
                    pending.append(dependency)
                    pending.extend(dependency + "." + item.name for item in node.names)
            elif isinstance(node, ast.Import):
                pending.extend(
                    item.name for item in node.names if item.name.startswith("src.")
                )


def test_business_identity_excludes_transport_configuration():
    prohibited = {
        "adapter_id",
        "connection_id",
        "secret_reference",
        "credentials",
        "endpoint",
        "lease_token",
        "retry_count",
        "webhook",
        "provider",
    }
    assert not prohibited.intersection(AccountingHandoffSnapshot.model_fields)
    assert not prohibited.intersection(
        ProjectBillingPreparationPayload.__dataclass_fields__
    )
    assert not prohibited.intersection(ProjectAccountingHandoffORM.__table__.columns.keys())


def test_one_delivery_record_per_scoped_handoff_not_per_adapter():
    unique_keys = {
        tuple(column.name for column in constraint.columns)
        for constraint in ProjectAccountingOutboxORM.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("tenant_id", "organization_id", "event_id") in unique_keys
    # Connector deletion cannot cascade into the canonical business evidence.
    assert all("organization_accounting_connectors" not in key.target_fullname
               for key in ProjectAccountingHandoffORM.__table__.foreign_keys)


def test_no_retired_publisher_or_unauthenticated_outcome_command():
    roots = [
        ROOT / "src/core/modules/project_management",
        ROOT / "src/infra/composition",
    ]
    retired = ("ProjectBillingPreparationPublisher", "def record_external_outcome(")
    for root in roots:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8-sig")
            assert not any(symbol in source for symbol in retired), path


def test_repository_and_delivery_services_do_not_own_commit():
    paths = [
        "src/core/modules/project_management/infrastructure/persistence/repositories/finance/accounting/handoff.py",
        "src/core/platform/application/integration/delivery_service.py",
        "src/infra/persistence/repositories/integration_delivery.py",
    ]
    for name in paths:
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8-sig"))
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "commit"
            for node in ast.walk(tree)
        ), name
