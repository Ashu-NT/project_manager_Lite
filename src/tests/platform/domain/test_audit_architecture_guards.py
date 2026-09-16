from __future__ import annotations

import inspect
import json

from src.core.platform.contract.repositories.history.audit.contracts import AuditRepository
from src.core.platform.domain.history.audit.audit_entry import (
    AUDIT_CATEGORIES,
    AUDIT_RESULTS,
    AuditEntry,
)
from src.core.platform.infrastructure.persistence.mappers.history.audit.audit_entry import (
    audit_entry_to_orm,
)
from src.core.shared.audit.redaction import redact_changed_fields, redact_sensitive


def _entry(**overrides) -> AuditEntry:
    fields = dict(
        operation="update",
        entity_type="user",
        entity_id="u1",
        module="platform",
    )
    fields.update(overrides)
    return AuditEntry.create(**fields)


# ---------------------------------------------------------------------------
# Immutability: append-only, no update/delete API surfaced to application code
# ---------------------------------------------------------------------------


def test_audit_repository_contract_exposes_no_update_or_delete() -> None:
    method_names = {
        name for name, _ in inspect.getmembers(AuditRepository, predicate=inspect.isfunction)
    }
    assert not any(name.startswith("update") for name in method_names)
    assert not any(name.startswith("delete") for name in method_names)
    assert not any(name.startswith("remove") for name in method_names)


def test_audit_entry_domain_object_has_no_mutation_helpers() -> None:
    """AuditEntry is a plain frozen-in-spirit evidence record: no method on it
    should let application code mutate a persisted entry in place."""
    method_names = {
        name
        for name, _ in inspect.getmembers(AuditEntry, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert method_names == {"create"}


# ---------------------------------------------------------------------------
# Redaction: secrets never reach persistence, real evidence values do
# ---------------------------------------------------------------------------


def test_redact_sensitive_masks_known_secret_keys() -> None:
    payload = {
        "password": "hunter2",
        "api_key": "abc123",
        "mfa_secret": "otpseed",
        "refresh_token": "rt-1",
        "name": "Ada",
    }
    redacted = redact_sensitive(payload)
    assert redacted["password"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["mfa_secret"] == "[REDACTED]"
    assert redacted["refresh_token"] == "[REDACTED]"
    assert redacted["name"] == "Ada"


def test_redact_sensitive_does_not_mask_boolean_or_none_flags_that_merely_name_a_marker() -> None:
    """A key containing a sensitive marker but holding a non-string (bool/None)
    value is a policy flag, not a secret container -- must survive untouched."""
    payload = {
        "must_change_password": True,
        "password_reset_required": False,
        "api_key_configured": None,
    }
    redacted = redact_sensitive(payload)
    assert redacted == payload


def test_redact_sensitive_recurses_into_nested_structures() -> None:
    payload = {"profile": {"password": "hunter2", "email": "a@example.com"}, "tags": [{"token": "t1"}]}
    redacted = redact_sensitive(payload)
    assert redacted["profile"]["password"] == "[REDACTED]"
    assert redacted["profile"]["email"] == "a@example.com"
    assert redacted["tags"][0]["token"] == "[REDACTED]"


def test_redact_changed_fields_masks_both_sides_of_a_sensitive_field() -> None:
    diff = {
        "password": {"before": "old-secret", "after": "new-secret"},
        "must_change_password": {"before": False, "after": True},
        "email": {"before": "a@example.com", "after": "b@example.com"},
    }
    redacted = redact_changed_fields(diff)
    assert redacted["password"] == {"before": "[REDACTED]", "after": "[REDACTED]"}
    assert redacted["must_change_password"] == {"before": False, "after": True}
    assert redacted["email"] == diff["email"]


def test_mapper_applies_redaction_to_every_evidence_field_before_persistence() -> None:
    """Redaction is enforced once, structurally, at the mapper boundary -- a
    producer that forgets to sanitize its own payload still can't leak a
    secret into Audit."""
    entry = _entry(
        before_data={"password": "old-secret"},
        after_data={"password": "new-secret", "name": "Ada"},
        changed_fields={"password": {"before": "old-secret", "after": "new-secret"}},
        metadata={"api_key": "abc123", "action": "user.update"},
    )
    orm_row = audit_entry_to_orm(entry)
    assert "old-secret" not in orm_row.before_data_json
    assert "new-secret" not in orm_row.after_data_json
    assert "old-secret" not in orm_row.changed_fields_json
    assert "abc123" not in orm_row.metadata_json
    assert json.loads(orm_row.after_data_json)["name"] == "Ada"
    assert json.loads(orm_row.metadata_json)["action"] == "user.update"


# ---------------------------------------------------------------------------
# Category / result classification: normalized, never silently invalid
# ---------------------------------------------------------------------------


def test_invalid_category_falls_back_to_compliance_rather_than_persisting_garbage() -> None:
    entry = _entry(category="NOT_A_REAL_CATEGORY")
    assert entry.category == "COMPLIANCE"


def test_invalid_result_falls_back_to_success_rather_than_persisting_garbage() -> None:
    entry = _entry(result="NOT_A_REAL_RESULT")
    assert entry.result == "SUCCESS"


def test_valid_categories_and_results_pass_through_unchanged() -> None:
    for category in AUDIT_CATEGORIES:
        assert _entry(category=category).category == category
    for result in AUDIT_RESULTS:
        assert _entry(result=result).result == result


# ---------------------------------------------------------------------------
# No generic dual-write helper: Activity and Audit are recorded independently
# by each producer, never coupled by a shared "record both" utility.
# ---------------------------------------------------------------------------


def test_no_shared_helper_couples_activity_and_audit_recording() -> None:
    import src.core.shared.activity.activity_recorder as activity_recorder_module
    import src.core.shared.audit.audit_recorder as audit_recorder_module

    activity_source = inspect.getsource(activity_recorder_module)
    audit_source = inspect.getsource(audit_recorder_module)
    assert "record_audit_entry" not in activity_source
    assert "record_activity" not in audit_source
