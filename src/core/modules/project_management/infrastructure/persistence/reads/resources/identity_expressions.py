from sqlalchemy import func

from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import (
    EmployeeORM,
)


def resource_display_name():
    """Employee identity stays Platform-owned; PM owns only the resource registration."""
    return func.coalesce(EmployeeORM.full_name, ResourceORM.name)


__all__ = ["resource_display_name"]
