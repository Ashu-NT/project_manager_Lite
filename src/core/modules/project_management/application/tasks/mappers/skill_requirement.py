from src.core.modules.project_management.application.tasks.dto.responses.skill_requirement import (
    TaskSkillRequirementResponseDto,
)
from src.core.modules.project_management.domain.resources.skills import TaskSkillRequirement


def map_skill_requirement(requirement: TaskSkillRequirement) -> TaskSkillRequirementResponseDto:
    return TaskSkillRequirementResponseDto(
        id=requirement.id,
        task_id=requirement.task_id,
        skill_code=requirement.skill_code,
        certification_code=requirement.certification_code,
        required_proficiency=requirement.required_proficiency.value,
        validation_mode=requirement.validation_mode.value,
        notes=requirement.notes,
        version=requirement.version,
    )
