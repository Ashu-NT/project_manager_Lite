from src.core.platform.importing import ImportFieldSpec

PROJECT_IMPORT_SCHEMA: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec("id", "Project ID"),
    ImportFieldSpec("name", "Name", required=True),
    ImportFieldSpec("description", "Description"),
    ImportFieldSpec("client_name", "Client"),
    ImportFieldSpec("client_contact", "Client Contact"),
    ImportFieldSpec("planned_budget", "Planned Budget"),
    ImportFieldSpec("currency", "Currency"),
    ImportFieldSpec("start_date", "Start Date"),
    ImportFieldSpec("end_date", "End Date"),
    ImportFieldSpec("status", "Status"),
)
