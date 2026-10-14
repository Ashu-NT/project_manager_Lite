"""Employee command handlers."""

from src.core.platform.application.master_data.employee.commands.employee_commands import (
    EmployeeCommandHandler,
)
from src.core.platform.application.master_data.employee.commands.employee_document_commands import (
    EmployeeDocumentCommandHandler,
)

__all__ = ["EmployeeCommandHandler", "EmployeeDocumentCommandHandler"]
