from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1

logger = logging.getLogger(__name__)

_CAPABILITY_PERMISSIONS = {
    "approve_baseline": "baseline.approve",
    "apply_leveling": "task.manage",
    "manage_skills": "resource.manage",
    "request_assignment_override": "approval.request",
    "import": "import.manage",
    "approve_pm_request": "approval.decide",
}


@QmlElement
@QmlUncreatable("PMCapabilityController is provided by the shell runtime.")
class PMCapabilityController(QObject):
    """
    Exposes six PM-scoped capability flags to QML.

    Unknown, incomplete, and failed evaluations are deny-safe. Call refresh()
    after a session or tenant/organization context change.
    """

    canApproveBaselineChanged = Signal()
    canApplyLevelingChanged = Signal()
    canManageSkillsChanged = Signal()
    canRequestAssignmentOverrideChanged = Signal()
    canImportChanged = Signal()
    canApprovePmRequestChanged = Signal()
    evaluationStateChanged = Signal()

    def __init__(
        self,
        *,
        auth_engine: Any | None = None,
        user_session_provider: Callable[[], Any | None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth_engine = auth_engine
        self._user_session_provider = user_session_provider
        self._can_approve_baseline = False
        self._can_apply_leveling = False
        self._can_manage_skills = False
        self._can_request_assignment_override = False
        self._can_import = False
        self._can_approve_pm_request = False
        self._evaluation_state = "unknown"
        self._recompute()

    # ── Q_PROPERTYs ──────────────────────────────────────────────────────────

    @Property(bool, notify=canApproveBaselineChanged)
    def canApproveBaseline(self) -> bool:
        return self._can_approve_baseline

    @Property(bool, notify=canApplyLevelingChanged)
    def canApplyLeveling(self) -> bool:
        return self._can_apply_leveling

    @Property(bool, notify=canManageSkillsChanged)
    def canManageSkills(self) -> bool:
        return self._can_manage_skills

    @Property(bool, notify=canRequestAssignmentOverrideChanged)
    def canRequestAssignmentOverride(self) -> bool:
        return self._can_request_assignment_override

    @Property(bool, notify=canImportChanged)
    def canImport(self) -> bool:
        return self._can_import

    @Property(bool, notify=canApprovePmRequestChanged)
    def canApprovePmRequest(self) -> bool:
        return self._can_approve_pm_request

    @Property(str, notify=evaluationStateChanged)
    def evaluationState(self) -> str:
        return self._evaluation_state

    # ── Slot ─────────────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        """Recompute all capability flags from the current session."""
        self._recompute()

    # ── Private ──────────────────────────────────────────────────────────────

    def _recompute(self) -> None:
        if self._auth_engine is None:
            self._deny_all("unavailable")
            return
        try:
            session = (
                self._user_session_provider()
                if self._user_session_provider is not None
                else None
            )
        except Exception:
            logger.warning("PM capability session lookup failed", exc_info=True)
            self._deny_all("error")
            return

        if not self._has_required_context(session):
            self._deny_all("unavailable")
            return

        results: dict[str, bool] = {}
        evaluation_failed = False
        for capability, permission_code in _CAPABILITY_PERMISSIONS.items():
            try:
                results[capability] = bool(
                    self._auth_engine.has_permission(session, permission_code)
                )
            except Exception:
                evaluation_failed = True
                results[capability] = False
                logger.warning(
                    "PM capability evaluation failed permission_code=%s",
                    permission_code,
                    exc_info=True,
                )

        self._set_can_approve_baseline(results["approve_baseline"])
        self._set_can_apply_leveling(results["apply_leveling"])
        self._set_can_manage_skills(results["manage_skills"])
        self._set_can_request_assignment_override(
            results["request_assignment_override"]
        )
        self._set_can_import(results["import"])
        self._set_can_approve_pm_request(results["approve_pm_request"])
        self._set_evaluation_state("error" if evaluation_failed else "ready")

    @staticmethod
    def _has_required_context(session: Any | None) -> bool:
        if session is None or getattr(session, "principal", None) is None:
            return False
        try:
            tenant_id = session.active_tenant_id()
            organization_id = session.active_organization_id()
        except Exception:
            logger.warning("PM capability context lookup failed", exc_info=True)
            return False
        return bool(str(tenant_id or "").strip() and str(organization_id or "").strip())

    def _deny_all(self, evaluation_state: str) -> None:
        self._set_can_approve_baseline(False)
        self._set_can_apply_leveling(False)
        self._set_can_manage_skills(False)
        self._set_can_request_assignment_override(False)
        self._set_can_import(False)
        self._set_can_approve_pm_request(False)
        self._set_evaluation_state(evaluation_state)

    def _set_evaluation_state(self, value: str) -> None:
        if value == self._evaluation_state:
            return
        self._evaluation_state = value
        self.evaluationStateChanged.emit()

    def _set_can_approve_baseline(self, v: bool) -> None:
        if v == self._can_approve_baseline:
            return
        self._can_approve_baseline = v
        self.canApproveBaselineChanged.emit()

    def _set_can_apply_leveling(self, v: bool) -> None:
        if v == self._can_apply_leveling:
            return
        self._can_apply_leveling = v
        self.canApplyLevelingChanged.emit()

    def _set_can_manage_skills(self, v: bool) -> None:
        if v == self._can_manage_skills:
            return
        self._can_manage_skills = v
        self.canManageSkillsChanged.emit()

    def _set_can_request_assignment_override(self, v: bool) -> None:
        if v == self._can_request_assignment_override:
            return
        self._can_request_assignment_override = v
        self.canRequestAssignmentOverrideChanged.emit()

    def _set_can_import(self, v: bool) -> None:
        if v == self._can_import:
            return
        self._can_import = v
        self.canImportChanged.emit()

    def _set_can_approve_pm_request(self, v: bool) -> None:
        if v == self._can_approve_pm_request:
            return
        self._can_approve_pm_request = v
        self.canApprovePmRequestChanged.emit()


__all__ = ["PMCapabilityController"]
