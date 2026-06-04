from src.core.platform.importing import ImportFieldSpec

TASK_IMPORT_SCHEMA: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec("id", "Task ID"),
    ImportFieldSpec("project_id", "Project ID"),
    ImportFieldSpec("project_name", "Project Name"),
    ImportFieldSpec("name", "Task Name", required=True),
    ImportFieldSpec("description", "Description"),
    ImportFieldSpec("start_date", "Start Date"),
    ImportFieldSpec("duration_days", "Duration Days"),
    ImportFieldSpec("priority", "Priority"),
    ImportFieldSpec("deadline", "Deadline"),
    ImportFieldSpec("status", "Status"),
    ImportFieldSpec("percent_complete", "Percent Complete"),
)
