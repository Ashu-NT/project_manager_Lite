from src.core.platform.importing import ImportFieldSpec

RESOURCE_IMPORT_SCHEMA: tuple[ImportFieldSpec, ...] = (
    ImportFieldSpec("id", "Resource ID"),
    ImportFieldSpec("name", "Name", required=True),
    ImportFieldSpec("role", "Role"),
    ImportFieldSpec("hourly_rate", "Hourly Rate"),
    ImportFieldSpec("is_active", "Active"),
    ImportFieldSpec("cost_type", "Cost Type"),
    ImportFieldSpec("currency_code", "Currency"),
    ImportFieldSpec("capacity_percent", "Capacity %"),
    ImportFieldSpec("address", "Address"),
    ImportFieldSpec("contact", "Contact"),
)
