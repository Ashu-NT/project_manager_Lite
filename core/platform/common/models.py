"""Compatibility facade for domain models.

New code should import focused models from ``core.domain`` modules.
This module re-exports all legacy names to preserve existing imports.
"""
from core.platform.approval.domain import ApprovalRequest, ApprovalStatus
from core.platform.access.domain import ProjectMembership
from core.platform.auth.domain import Permission, Role, RolePermissionBinding, UserAccount, UserRoleBinding
from core.platform.audit.domain import AuditLogEntry
from core.platform.org.domain import Employee, EmploymentType, Organization
from core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus, WorkEntry
from core.modules.project_management.domain.baseline import BaselineTask, ProjectBaseline
from core.modules.project_management.domain.calendar import CalendarEvent, Holiday, WorkingCalendar
from core.modules.project_management.domain.collaboration import (
    CollaborationInboxItem,
    CollaborationMentionCandidate,
    CollaborationNotificationItem,
    TaskPresence,
    TaskPresenceStatusItem,
    TaskComment,
)
from core.modules.project_management.domain.cost import CostItem
from core.modules.project_management.domain.enums import CostType, DependencyType, ProjectStatus, TaskStatus, WorkerType
from core.modules.project_management.domain.identifiers import generate_id
from core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioScenarioComparison,
    PortfolioScenario,
    PortfolioScenarioEvaluation,
)
from core.modules.project_management.domain.project import Project, ProjectResource
from core.modules.project_management.domain.register import (
    RegisterEntry,
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from core.modules.project_management.domain.resource import Resource
from core.modules.project_management.domain.task import Task, TaskAssignment, TaskDependency

__all__ = [
    "generate_id",
    "ProjectStatus",
    "TaskStatus",
    "DependencyType",
    "CostType",
    "WorkerType",
    "EmploymentType",
    "ProjectMembership",
    "Employee",
    "Organization",
    "Project",
    "ProjectResource",
    "CollaborationMentionCandidate",
    "TaskComment",
    "CollaborationInboxItem",
    "CollaborationNotificationItem",
    "TaskPresence",
    "TaskPresenceStatusItem",
    "RegisterEntry",
    "RegisterEntryType",
    "RegisterEntrySeverity",
    "RegisterEntryStatus",
    "PortfolioIntakeStatus",
    "PortfolioIntakeItem",
    "PortfolioScenario",
    "PortfolioScenarioEvaluation",
    "PortfolioScenarioComparison",
    "Task",
    "Resource",
    "TaskAssignment",
    "TaskDependency",
    "TimeEntry",
    "WorkEntry",
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
