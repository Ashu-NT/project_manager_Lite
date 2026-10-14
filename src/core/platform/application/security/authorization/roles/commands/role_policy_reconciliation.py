from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.application.security.auth.session.session_utils import (
    rotate_session_revision,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.security.authorization.roles.dto import (
    RolePolicyReconciliationPlan,
    RolePolicyReconciliationResult,
)
from src.core.platform.application.security.authorization.roles.queries.role_policy_reconciliation import (
    RolePolicyReconciliationQueryHandler,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.security.auth import (
    AuthPolicyReconciliationRepository,
    AuthSessionRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
)
from src.core.platform.contract.uow.security.auth_unit_of_work import (
    AuthUnitOfWorkFactory,
)
from src.core.platform.domain.security.auth import (
    RolePermissionBinding,
    UserSessionContext,
)
from src.core.platform.domain.security.auth.events import RolePolicyReconciled
from src.core.platform.domain.security.authorization.roles import (
    AuthPolicyReconciliation,
)
from src.core.platform.domain.security.authorization.roles.role_permission_catalog import (
    DEFAULT_ROLE_PERMISSIONS,
)
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)


class RolePolicyReconciliationCommandHandler:
    def __init__(
        self,
        *,
        session: Session,
        queries: RolePolicyReconciliationQueryHandler,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
        role_permission_repo: RolePermissionRepository,
        user_repo: UserRepository,
        auth_session_repo: AuthSessionRepository,
        reconciliation_repo: AuthPolicyReconciliationRepository,
        user_session: UserSessionContext,
        transactional_dispatcher: TransactionalEventDispatcher | None,
        post_commit_bus: PostCommitEventPublisher | None,
        uow_factory: AuthUnitOfWorkFactory,
    ) -> None:
        self._session = session
        self._queries = queries
        self._role_repo = role_repo
        self._permission_repo = permission_repo
        self._role_permission_repo = role_permission_repo
        self._user_repo = user_repo
        self._auth_session_repo = auth_session_repo
        self._reconciliation_repo = reconciliation_repo
        self._user_session = user_session
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus
        self._uow_factory = uow_factory

    def _uow(self):
        return self._uow_factory.create(
            session=self._session,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
        )

    def apply(
        self,
        *,
        expected_version: int,
        expected_change_set_hash: str,
    ) -> RolePolicyReconciliationResult:
        require_permission(
            self._user_session,
            "platform.admin",
            operation_label="apply system role policy reconciliation",
        )
        expected_hash = str(expected_change_set_hash or "").strip().lower()
        no_op_result: RolePolicyReconciliationResult | None = None
        applied_at: datetime | None = None
        plan: RolePolicyReconciliationPlan | None = None
        revoked_session_count = 0
        try:
            with self._uow() as uow:
                with self._session.begin_nested():
                    plan = self._queries.build_plan(lock_policy_state=True)
                    if int(expected_version) != plan.current_version:
                        raise BusinessRuleError(
                            "Authorization policy version changed after review.",
                            code="ROLE_POLICY_VERSION_MISMATCH",
                        )
                    if expected_hash != plan.change_set_hash:
                        raise BusinessRuleError(
                            "Authorization policy drift changed after review.",
                            code="ROLE_POLICY_CHANGE_SET_MISMATCH",
                        )
                    if plan.missing_role_names or plan.missing_permission_codes:
                        raise BusinessRuleError(
                            "Managed role or permission definitions are missing.",
                            code="ROLE_POLICY_DEFINITION_MISSING",
                        )
                    if plan.current_version > plan.target_version:
                        raise BusinessRuleError(
                            "Persisted authorization policy is newer than this application.",
                            code="ROLE_POLICY_VERSION_AHEAD",
                        )
                    if plan.current_version == plan.target_version:
                        if plan.has_changes:
                            raise BusinessRuleError(
                                "Managed system-role bindings drifted after policy application.",
                                code="ROLE_POLICY_UNEXPECTED_DRIFT",
                            )
                        no_op_result = RolePolicyReconciliationResult(
                            plan=plan,
                            applied=False,
                            revoked_session_count=0,
                        )
                    else:
                        role_map = {
                            role.name: role
                            for role in self._role_repo.list_all()
                            if (
                                role.is_system and role.name in DEFAULT_ROLE_PERMISSIONS
                            )
                        }
                        permission_map = {
                            permission.code: permission
                            for permission in self._permission_repo.list_all()
                        }
                        for change in plan.removals:
                            self._role_permission_repo.delete(
                                role_map[change.role_name].id,
                                permission_map[change.permission_code].id,
                            )
                        for change in plan.additions:
                            role = role_map[change.role_name]
                            permission = permission_map[change.permission_code]
                            self._role_permission_repo.add(
                                RolePermissionBinding.create(
                                    role_id=role.id,
                                    permission_id=permission.id,
                                )
                            )

                        applied_at = datetime.now(UTC)
                        for role in role_map.values():
                            if not self._role_repo.set_policy_version(
                                role.id,
                                policy_version=plan.target_version,
                                updated_at=applied_at,
                            ):
                                raise BusinessRuleError(
                                    "Managed system role changed during policy "
                                    "reconciliation.",
                                    code="ROLE_POLICY_CONCURRENT_ROLE_CHANGE",
                                )
                        revoked_session_count = self._invalidate_affected_users(
                            plan.affected_user_ids,
                            revoked_at=applied_at,
                        )
                        self._reconciliation_repo.add(
                            AuthPolicyReconciliation(
                                id=generate_id(),
                                policy_name=plan.policy_name,
                                from_version=plan.current_version,
                                to_version=plan.target_version,
                                change_set_hash=plan.change_set_hash,
                                applied_at=applied_at,
                                applied_by_user_id=self._actor_user_id(),
                                rollback_json=plan.rollback_json,
                            )
                        )
                if no_op_result is None and applied_at is not None:
                    uow.record_event(
                        RolePolicyReconciled(
                            policy_name=plan.policy_name,
                            from_version=plan.current_version,
                            to_version=plan.target_version,
                            occurred_at=applied_at,
                        )
                    )
                uow.commit()
        except IntegrityError as exc:
            raise BusinessRuleError(
                "Authorization policy was reconciled concurrently.",
                code="ROLE_POLICY_CONCURRENT_APPLY",
            ) from exc

        if no_op_result is not None:
            return no_op_result
        return RolePolicyReconciliationResult(
            plan=plan,
            applied=True,
            revoked_session_count=revoked_session_count,
        )

    def _invalidate_affected_users(
        self,
        user_ids: tuple[str, ...],
        *,
        revoked_at: datetime,
    ) -> int:
        revoked_session_count = 0
        for user_id in user_ids:
            user = self._user_repo.get(user_id)
            if user is None:
                continue
            rotate_session_revision(user)
            user.session_expires_at = revoked_at
            user.updated_at = revoked_at
            for auth_session in self._auth_session_repo.list_by_user(user.id):
                if auth_session.revoked_at is not None:
                    continue
                auth_session.revoked_at = revoked_at
                auth_session.updated_at = revoked_at
                self._auth_session_repo.update(auth_session)
                revoked_session_count += 1
            self._user_repo.update(user)
        return revoked_session_count

    def _actor_user_id(self) -> str:
        principal = self._user_session.principal
        if principal is None:
            raise BusinessRuleError(
                "Authentication is required for policy reconciliation.",
                code="AUTHENTICATION_REQUIRED",
            )
        return principal.user_id
