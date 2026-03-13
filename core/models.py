"""Compatibility facade for domain models.

New code should import focused models from ``core.domain`` modules.
This module re-exports all legacy names to preserve existing imports.
"""

from core.domain.approval import ApprovalRequest, ApprovalStatus
from core.domain.access import ProjectMembership
from core.domain.auth import Permission, Role, RolePermissionBinding, UserAccount, UserRoleBinding
from core.domain.audit import AuditLogEntry
from core.domain.baseline import BaselineTask, ProjectBaseline
from core.domain.calendar import CalendarEvent, Holiday, WorkingCalendar
from core.domain.collaboration import CollaborationInboxItem, CollaborationMentionCandidate, TaskComment
from core.domain.cost import CostItem
from core.domain.enums import CostType, DependencyType, ProjectStatus, TaskStatus
from core.domain.identifiers import generate_id
from core.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioScenario,
    PortfolioScenarioEvaluation,
)
from core.domain.project import Project, ProjectResource
from core.domain.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from core.domain.resource import Resource
from core.domain.task import Task, TaskAssignment, TaskDependency, TimeEntry, TimesheetPeriod, TimesheetPeriodStatus

__all__ = [
    "generate_id",
    "ProjectStatus",
    "TaskStatus",
    "DependencyType",
    "CostType",
    "ProjectMembership",
    "Project",
    "ProjectResource",
    "CollaborationMentionCandidate",
    "TaskComment",
    "CollaborationInboxItem",
    "RegisterEntry",
    "RegisterEntryType",
    "RegisterEntrySeverity",
    "RegisterEntryStatus",
    "PortfolioIntakeStatus",
    "PortfolioIntakeItem",
    "PortfolioScenario",
    "PortfolioScenarioEvaluation",
    "Task",
    "Resource",
    "TaskAssignment",
    "TaskDependency",
    "TimeEntry",
    "TimesheetPeriod",
    "TimesheetPeriodStatus",
    "CostItem",
    "CalendarEvent",
    "WorkingCalendar",
    "Holiday",
    "ProjectBaseline",
    "BaselineTask",
    "UserAccount",
    "Role",
    "Permission",
    "UserRoleBinding",
    "RolePermissionBinding",
    "AuditLogEntry",
    "ApprovalStatus",
    "ApprovalRequest",
]
