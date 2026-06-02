from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlElement, QmlUncreatable

QML_IMPORT_NAME = "ProjectManagement.Controllers"
QML_IMPORT_MAJOR_VERSION = 1


@QmlElement
@QmlUncreatable("PMCapabilityController is provided by the shell runtime.")
class PMCapabilityController(QObject):
    """
    Exposes six PM-scoped capability flags to QML.

    Defaults to fully permissive (all True) when no auth_engine is provided.
    Call refresh() after a session change to recompute flags.
    """

    canApproveBaselineChanged = Signal()
    canApplyLevelingChanged = Signal()
    canManageSkillsChanged = Signal()
    canRequestAssignmentOverrideChanged = Signal()
    canImportChanged = Signal()
    canApprovePmRequestChanged = Signal()

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
        self._can_approve_baseline = True
        self._can_apply_leveling = True
        self._can_manage_skills = True
        self._can_request_assignment_override = True
        self._can_import = True
        self._can_approve_pm_request = True
        if auth_engine is not None:
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

    # ── Slot ─────────────────────────────────────────────────────────────────

    @Slot()
    def refresh(self) -> None:
        """Recompute all capability flags from the current session."""
        self._recompute()

    # ── Private ──────────────────────────────────────────────────────────────

    def _recompute(self) -> None:
        if self._auth_engine is None:
            return
        session = (
            self._user_session_provider()
            if self._user_session_provider is not None
            else None
        )
        self._set_can_approve_baseline(self._check("pm.baseline.approve", session))
        self._set_can_apply_leveling(self._check("pm.schedule.apply_leveling", session))
        self._set_can_manage_skills(self._check("pm.resource.manage_skills", session))
        self._set_can_request_assignment_override(
            self._check("pm.assignment.request_override", session)
        )
        self._set_can_import(self._check("pm.import.execute", session))
        self._set_can_approve_pm_request(self._check("pm.request.approve", session))

    def _check(self, permission_code: str, session: Any | None) -> bool:
        try:
            return bool(self._auth_engine.has_permission(session, permission_code))
        except Exception:
            return True

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
