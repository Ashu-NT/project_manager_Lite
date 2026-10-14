"""Resource catalog use-case contracts."""

from src.core.modules.project_management.contracts.use_cases.resources.commands import (
    ResourceAddCertificationCommand,
    ResourceAddSkillCommand,
    ResourceCreateCommand,
    ResourceLifecycleCommand,
    ResourcePurgeCommand,
    ResourceRemoveCertificationCommand,
    ResourceRemoveSkillCommand,
    ResourceUpdateCertificationCommand,
    ResourceUpdateCommand,
    ResourceUpdateSkillCommand,
)

__all__ = [
    "ResourceAddCertificationCommand",
    "ResourceAddSkillCommand",
    "ResourceCreateCommand",
    "ResourceLifecycleCommand",
    "ResourcePurgeCommand",
    "ResourceRemoveCertificationCommand",
    "ResourceRemoveSkillCommand",
    "ResourceUpdateCertificationCommand",
    "ResourceUpdateCommand",
    "ResourceUpdateSkillCommand",
]
