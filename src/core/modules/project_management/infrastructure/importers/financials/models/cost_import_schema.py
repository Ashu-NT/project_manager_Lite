from src.core.platform.importing import ImportFieldSpec

COST_IMPORT_SCHEMA: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec("id", "Cost ID"),
    ImportFieldSpec("project_id", "Project ID"),
    ImportFieldSpec("project_name", "Project Name"),
    ImportFieldSpec("task_id", "Task ID"),
    ImportFieldSpec("task_name", "Task Name"),
    ImportFieldSpec("description", "Description", required=True),
    ImportFieldSpec("planned_amount", "Planned Amount"),
    ImportFieldSpec("committed_amount", "Committed Amount"),
    ImportFieldSpec("actual_amount", "Actual Amount"),
    ImportFieldSpec("cost_type", "Cost Type"),
    ImportFieldSpec("currency_code", "Currency"),
    ImportFieldSpec("incurred_date", "Incurred Date"),
)
