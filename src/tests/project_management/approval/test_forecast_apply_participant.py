from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastVersionChanged,
    ForecastVersionChangeType,
)
from src.core.modules.project_management.application.financials.forecasts.version_service import (
    ForecastVersionService,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
    ForecastStatus,
)
from src.core.modules.project_management.infrastructure.approval.forecast_apply_participant import (
    ForecastApprovalParticipant,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.approval import ApprovalRequest
from src.infra.composition.approval_apply_dependencies.forecast import (
    build_forecast_approval_deps,
)
from src.infra.persistence.orm.base import Base


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user = auth.authenticate(username, password)
    services["user_session"].set_principal(auth.build_principal(user))


def _submitted_forecast(services, session):
    project = services["project_service"].create_project(
        "Forecast approval project", financial_currency_code="USD"
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="FORECAST-APPROVAL", name="Forecast approval"
    )
    service = services["forecast_version_service"]
    forecast = service.create_forecast(
        project.id,
        name="Approval candidate",
        as_of_date=date(2026, 9, 1),
        generation_mode=ForecastGenerationMode.MANUAL,
        created_by="admin",
    )
    service.add_line(
        forecast.id,
        cost_code_id=cost_code.id,
        description="Remaining estimate",
        amount=Decimal("100.00"),
        source_kind=ForecastLineSourceKind.MANUAL,
        source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin",
        expected_forecast_version=forecast.row_version,
    )
    forecast = service.get_forecast(forecast.id)
    forecast = service.submit_forecast(
        forecast.id,
        submitted_by="admin",
        expected_version=forecast.row_version,
    )
    session.expire_all()
    return project, forecast


def _request(forecast) -> ApprovalRequest:
    return ApprovalRequest.create(
        request_type="forecast.approve",
        entity_type="project_forecast",
        entity_id=forecast.id,
        tenant_id=forecast.tenant_id,
        organization_id=forecast.organization_id,
        project_id=forecast.project_id,
        payload={
            "forecast_id": forecast.id,
            "expected_version": forecast.row_version,
            "notes": "Independent review",
        },
        requested_by_user_id="requester-1",
        requested_by_username="requester",
    )


def _deps(services, session):
    return build_forecast_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
    )


def test_participant_approves_on_supplied_session_and_returns_typed_event(
    services, session
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project, forecast = _submitted_forecast(services, session)
    deps = _deps(services, session)

    result = ForecastApprovalParticipant().apply(_request(forecast), deps)

    approved = deps.forecast_service._forecast_repo.get(forecast.id)
    assert approved.status is ForecastStatus.APPROVED
    assert approved.approved_by == services["user_session"].principal.user_id
    assert result.post_commit_events == ()
    assert result.domain_events == (
        ForecastVersionChanged(
            tenant_id=forecast.tenant_id,
            organization_id=forecast.organization_id,
            project_id=project.id,
            forecast_id=forecast.id,
            change_type=ForecastVersionChangeType.APPROVED,
            occurred_at=approved.approved_at,
        ),
    )


def test_participant_never_owns_commit_or_rollback(
    services, session, monkeypatch
) -> None:
    _login(services, "admin", "ChangeMe123!")
    _, forecast = _submitted_forecast(services, session)
    deps = _deps(services, session)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("ApprovalService owns transaction completion")

    monkeypatch.setattr(type(session), "commit", _forbidden)
    monkeypatch.setattr(type(session), "rollback", _forbidden)

    ForecastApprovalParticipant().reject(_request(forecast), deps)


def test_participant_reject_requires_authenticated_deciding_actor(
    services, session
) -> None:
    _login(services, "admin", "ChangeMe123!")
    _, forecast = _submitted_forecast(services, session)
    deps = build_forecast_approval_deps(
        session,
        user_session=_BlankUserSession(),
        tenant_context_service=services["tenant_context_service"],
    )

    with pytest.raises(BusinessRuleError, match="authenticated principal"):
        ForecastApprovalParticipant().reject(_request(forecast), deps)


def test_dependencies_are_bound_to_the_approval_uow_session(tmp_path, services) -> None:
    engine_a = create_engine(f"sqlite:///{tmp_path}/forecast_deps_a.db", future=True)
    engine_b = create_engine(f"sqlite:///{tmp_path}/forecast_deps_b.db", future=True)
    Base.metadata.create_all(engine_a)
    Base.metadata.create_all(engine_b)
    session_a = sessionmaker(bind=engine_a, future=True)()
    session_b = sessionmaker(bind=engine_b, future=True)()
    try:
        deps_a = _deps(services, session_a)
        deps_b = _deps(services, session_b)

        assert deps_a.forecast_service._session is session_a
        assert deps_b.forecast_service._session is session_b
        assert deps_a.forecast_service._forecast_repo.session is session_a
        assert deps_b.forecast_service._forecast_repo.session is session_b
        assert deps_a.forecast_service is not deps_b.forecast_service
        assert deps_a.forecast_service._enterprise_audit_service._session is session_a
        assert deps_b.forecast_service._enterprise_audit_service._session is session_b
        assert deps_a.forecast_service._approval_service is None
        assert deps_b.forecast_service._approval_service is None
    finally:
        session_a.close()
        session_b.close()


def test_platform_approval_request_enforces_separation_of_duties(
    services, session
) -> None:
    _login(services, "admin", "ChangeMe123!")
    _, forecast = _submitted_forecast(services, session)
    result = services["forecast_version_service"].request_forecast_approval(
        forecast.id,
        expected_version=forecast.row_version,
        notes="Review independently",
    )

    requester_view = services["finance_workspace_query"].get_forecast_workspace(
        forecast.project_id, selected_forecast_id=forecast.id
    )
    requester_row = requester_view.versions.items[0]
    assert requester_row.approval_request_id == result.approval_request_id
    assert requester_row.can_approve is False
    assert requester_row.can_reject is False

    with pytest.raises(BusinessRuleError) as exc:
        services["approval_service"].approve_and_apply(result.approval_request_id)
    assert exc.value.code == "APPROVAL_SELF_DECISION_FORBIDDEN"

    services["auth_service"].register_user(
        "forecast-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "forecast-reviewer", "StrongPass123")
    reviewer_view = services["finance_workspace_query"].get_forecast_workspace(
        forecast.project_id, selected_forecast_id=forecast.id
    )
    reviewer_row = reviewer_view.versions.items[0]
    assert reviewer_row.can_approve is True
    assert reviewer_row.can_reject is True
    services["approval_service"].approve_and_apply(
        result.approval_request_id, note="Approved independently"
    )

    session.expire_all()
    approved = services["forecast_version_service"].get_forecast(forecast.id)
    assert approved.status is ForecastStatus.APPROVED
    assert approved.approved_by == services["user_session"].principal.user_id


def test_generation_is_denied_without_forecast_manage_permission(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = services["project_service"].create_project(
        "Forecast authorization project", financial_currency_code="USD"
    )
    user_session = services["user_session"]
    original = user_session.principal
    user_session.set_principal(
        replace(
            original,
            permissions=frozenset(),
            scoped_access={},
            project_access={},
        )
    )
    try:
        with pytest.raises(BusinessRuleError) as exc:
            services["forecast_generation_service"].generate_draft(
                project.id,
                name="Forbidden forecast",
                as_of_date=date(2026, 9, 1),
                generated_by=original.user_id,
            )
        assert exc.value.code == "PERMISSION_DENIED"
    finally:
        user_session.set_principal(original)


def test_platform_approval_rolls_back_forecast_when_participant_fails(
    services, session, monkeypatch
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project, forecast = _submitted_forecast(services, session)
    result = services["forecast_version_service"].request_forecast_approval(
        forecast.id,
        expected_version=forecast.row_version,
    )
    services["auth_service"].register_user(
        "forecast-rollback-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "forecast-rollback-reviewer", "StrongPass123")

    apply_decision = ForecastVersionService._apply_approval_decision

    def _fail_after_forecast_transition(service, **kwargs):
        apply_decision(service, **kwargs)
        raise RuntimeError("injected participant failure")

    monkeypatch.setattr(
        ForecastVersionService,
        "_apply_approval_decision",
        _fail_after_forecast_transition,
    )

    with pytest.raises(RuntimeError, match="injected participant failure"):
        services["approval_service"].approve_and_apply(result.approval_request_id)

    session.expire_all()
    unchanged = services["forecast_version_service"].get_forecast(forecast.id)
    pending = next(
        request
        for request in services["approval_service"].list_pending(project_id=project.id)
        if request.id == result.approval_request_id
    )
    assert unchanged.status is ForecastStatus.SUBMITTED
    assert pending.status.value == "PENDING"


class _BlankUserSession:
    principal = None
