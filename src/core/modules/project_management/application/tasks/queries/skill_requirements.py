from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.tasks.dto.responses.skill_requirement import (
    TaskSkillRequirementResponseDto,
)
from src.core.modules.project_management.application.tasks.mappers.skill_requirement import (
    map_skill_requirement,
)


def query_skill_requirements(
    validator: AssignmentSkillValidator, task_id: str
) -> tuple[TaskSkillRequirementResponseDto, ...]:
    return tuple(map_skill_requirement(requirement) for requirement in validator.list_requirements(task_id))
