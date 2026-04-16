from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.importing import ImportFieldSpec


MAINTENANCE_MODULE_CODE = "maintenance_management"


@dataclass(frozen=True)
class MaintenanceWorkbookSheetContract:
    sheet_name: str
    entity_label: str
    owner_module_code: str
    description: str
    key_field: str
    field_specs: tuple[ImportFieldSpec, ...]
    operation_key: str | None = None
    depends_on_sheets: tuple[str, ...] = ()


def _field(key: str, label: str, *, required: bool = False) -> ImportFieldSpec:
    return ImportFieldSpec(key=key, label=label, required=required)


def _sheet(
    *,
    sheet_name: str,
    entity_label: str,
    owner_module_code: str,
    description: str,
    key_field: str,
    field_specs: tuple[ImportFieldSpec, ...],
    operation_key: str | None = None,
    depends_on_sheets: tuple[str, ...] = (),
) -> MaintenanceWorkbookSheetContract:
    return MaintenanceWorkbookSheetContract(
        sheet_name=sheet_name,
        entity_label=entity_label,
        owner_module_code=owner_module_code,
        description=description,
        key_field=key_field,
        field_specs=field_specs,
        operation_key=operation_key,
        depends_on_sheets=depends_on_sheets,
    )


MAINTENANCE_WORKBOOK_SHEETS: tuple[MaintenanceWorkbookSheetContract, ...] = (
    _sheet(
        sheet_name="Locations",
        entity_label="Maintenance Locations",
        owner_module_code=MAINTENANCE_MODULE_CODE,
        description="Physical maintenance locations and hierarchy beneath the shared site context.",
        key_field="location_code",
        operation_key="maintenance_locations",
        field_specs=(
            _field("location_code", "Location Code", required=True),
            _field("site_code", "Site Code", required=True),
            _field("location_name", "Location Name", required=True),
            _field("parent_location_code", "Parent Location Code"),
            _field("location_type", "Location Type"),
            _field("criticality", "Criticality"),
            _field("status", "Status"),
            _field("notes", "Notes"),
        ),
    ),
    _sheet(
        sheet_name="Systems",
        entity_label="Maintenance Systems",
        owner_module_code=MAINTENANCE_MODULE_CODE,
        description="Maintainable systems aligned to site and location hierarchy.",
        key_field="system_code",
        operation_key="maintenance_systems",
        depends_on_sheets=("Locations",),
        field_specs=(
            _field("system_code", "System Code", required=True),
            _field("site_code", "Site Code", required=True),
            _field("location_code", "Location Code"),
            _field("system_name", "System Name", required=True),
            _field("parent_system_code", "Parent System Code"),
            _field("system_type", "System Type"),
            _field("status", "Status"),
            _field("notes", "Notes"),
        ),
    ),
    _sheet(
        sheet_name="Assets",
        entity_label="Assets",
        owner_module_code=MAINTENANCE_MODULE_CODE,
        description="Maintainable asset register with hierarchy and linked parties.",
        key_field="asset_code",
        operation_key="maintenance_assets",
        depends_on_sheets=("Locations", "Systems", "Parties", "StockItems"),
        field_specs=(
            _field("asset_code", "Asset Code", required=True),
            _field("site_code", "Site Code", required=True),
            _field("location_code", "Location Code", required=True),
            _field("system_code", "System Code"),
            _field("parent_asset_code", "Parent Asset Code"),
            _field("asset_name", "Asset Name", required=True),
            _field("asset_class", "Asset Class"),
            _field("linked_item_code", "Linked Item Code"),
            _field("manufacturer_party_code", "Manufacturer Party Code"),
            _field("supplier_party_code", "Supplier Party Code"),
            _field("serial_number", "Serial Number"),
            _field("criticality", "Criticality"),
            _field("status", "Status"),
            _field("notes", "Notes"),
        ),
    ),
    _sheet(
        sheet_name="AssetComponents",
        entity_label="Asset Components",
        owner_module_code=MAINTENANCE_MODULE_CODE,
        description="Nested replaceable components beneath an asset.",
        key_field="component_code",
        operation_key="maintenance_asset_components",
        depends_on_sheets=("Assets", "Parties"),
        field_specs=(
            _field("component_code", "Component Code", required=True),
            _field("asset_code", "Asset Code", required=True),
            _field("parent_component_code", "Parent Component Code"),
            _field("component_name", "Component Name", required=True),
            _field("component_type", "Component Type"),
            _field("manufacturer_party_code", "Manufacturer Party Code"),
            _field("serial_number", "Serial Number"),
            _field("status", "Status"),
            _field("notes", "Notes"),
        ),
    ),
    _sheet(
        sheet_name="Sensors",
        entity_label="Sensors",
        owner_module_code=MAINTENANCE_MODULE_CODE,
        description="Counters, meters, and sensors that may drive maintenance triggers.",
        key_field="sensor_code",
        operation_key="maintenance_sensors",
        depends_on_sheets=("Assets", "AssetComponents"),
        field_specs=(
            _field("sensor_code", "Sensor Code", required=True),
            _field("asset_code", "Asset Code"),
            _field("component_code", "Component Code"),
            _field("sensor_name", "Sensor Name", required=True),
            _field("sensor_type", "Sensor Type"),
            _field("reading_uom", "Reading UOM"),
            _field("source_key", "Source Key"),
            _field("status", "Status"),
            _field("notes", "Notes"),
        ),
    ),
    _sheet(
        sheet_name="Parties",
        entity_label="Shared Parties",
        owner_module_code="platform",
        description="Shared supplier, manufacturer, and vendor references maintained by the platform.",
        key_field="party_code",
        field_specs=(
            _field("party_code", "Party Code", required=True),
            _field("party_type", "Party Type"),
            _field("display_name", "Display Name", required=True),
            _field("status", "Status"),
        ),
    ),
    _sheet(
        sheet_name="TaskTemplates",
        entity_label="Task Templates",
        owner_module_code=MAINTENANCE_MODULE_CODE,
        description="Reusable maintenance tasks or job-plan steps independent of trigger logic.",
        key_field="task_template_code",
        operation_key="maintenance_task_templates",
        depends_on_sheets=("DocumentStructures",),
        field_specs=(
            _field("task_template_code", "Task Template Code", required=True),
            _field("title", "Title", required=True),
            _field("work_type", "Work Type"),
            _field("discipline", "Discipline"),
            _field("default_priority", "Default Priority"),
            _field("estimated_duration_hours", "Estimated Duration Hours"),
            _field("document_structure_code", "Document Structure Code"),
            _field("notes", "Notes"),
        ),
    ),
    _sheet(
        sheet_name="TaskStepTemplates",
        entity_label="Task Step Templates",
        owner_module_code=MAINTENANCE_MODULE_CODE,
        description="Step-level execution guidance for a task template.",
        key_field="step_code",
        operation_key="maintenance_task_step_templates",
        depends_on_sheets=("TaskTemplates",),
        field_specs=(
            _field("task_template_code", "Task Template Code", required=True),
            _field("step_code", "Step Code", required=True),
            _field("step_sequence", "Step Sequence", required=True),
            _field("instruction", "Instruction", required=True),
            _field("requires_photo", "Requires Photo"),
            _field("requires_measurement", "Requires Measurement"),
            _field("measurement_uom", "Measurement UOM"),
            _field("mandatory", "Mandatory"),
        ),
    ),
    _sheet(
        sheet_name="PreventivePlans",
        entity_label="Preventive Plans",
        owner_module_code=MAINTENANCE_MODULE_CODE,
        description="Calendar, counter, and hybrid preventive plan headers.",
        key_field="plan_code",
        operation_key="maintenance_preventive_plans",
        depends_on_sheets=("Assets", "Systems", "Locations", "Sensors"),
        field_specs=(
            _field("plan_code", "Plan Code", required=True),
            _field("asset_code", "Asset Code"),
            _field("system_code", "System Code"),
            _field("location_code", "Location Code"),
            _field("trigger_mode", "Trigger Mode", required=True),
            _field("calendar_frequency_unit", "Calendar Frequency Unit"),
            _field("calendar_frequency_value", "Calendar Frequency Value"),
            _field("sensor_code", "Sensor Code"),
            _field("sensor_threshold", "Sensor Threshold"),
            _field("status", "Status"),
        ),
    ),
    _sheet(
        sheet_name="PreventivePlanTasks",
        entity_label="Preventive Plan Tasks",
        owner_module_code=MAINTENANCE_MODULE_CODE,
        description="Task-template assignments and trigger overrides per preventive plan.",
        key_field="line_ref",
        operation_key="maintenance_preventive_plan_tasks",
        depends_on_sheets=("PreventivePlans", "TaskTemplates", "Sensors"),
        field_specs=(
            _field("plan_code", "Plan Code", required=True),
            _field("line_ref", "Line Ref", required=True),
            _field("task_template_code", "Task Template Code", required=True),
            _field("trigger_scope", "Trigger Scope"),
            _field("trigger_mode_override", "Trigger Mode Override"),
            _field("calendar_frequency_unit_override", "Calendar Frequency Unit Override"),
            _field("calendar_frequency_value_override", "Calendar Frequency Value Override"),
            _field("sensor_code_override", "Sensor Code Override"),
            _field("sensor_threshold_override", "Sensor Threshold Override"),
            _field("mandatory", "Mandatory"),
        ),
    ),
    _sheet(
        sheet_name="StockItems",
        entity_label="Inventory Items",
        owner_module_code="inventory_procurement",
        description="Cross-module spare and consumable items referenced by maintenance assets and plans.",
        key_field="item_code",
        field_specs=(
            _field("item_code", "Item Code", required=True),
            _field("name", "Item Name", required=True),
            _field("category_code", "Category Code"),
            _field("item_type", "Item Type"),
            _field("stock_uom", "Stock UOM"),
        ),
    ),
    _sheet(
        sheet_name="Storerooms",
        entity_label="Storerooms",
        owner_module_code="inventory_procurement",
        description="Inventory storerooms used by maintenance material readiness and issue flows.",
        key_field="storeroom_code",
        field_specs=(
            _field("storeroom_code", "Storeroom Code", required=True),
            _field("site_code", "Site Code", required=True),
            _field("name", "Storeroom Name", required=True),
            _field("status", "Status"),
        ),
    ),
    _sheet(
        sheet_name="StockBalances",
        entity_label="Stock Balances",
        owner_module_code="inventory_procurement",
        description="Inventory balance snapshot used by rollout validation and material readiness checks.",
        key_field="line_ref",
        field_specs=(
            _field("line_ref", "Line Ref", required=True),
            _field("item_code", "Item Code", required=True),
            _field("storeroom_code", "Storeroom Code", required=True),
            _field("on_hand_qty", "On Hand Qty"),
            _field("reserved_qty", "Reserved Qty"),
        ),
    ),
    _sheet(
        sheet_name="Documents",
        entity_label="Shared Documents",
        owner_module_code="platform",
        description="Shared document records that maintenance entities can link to.",
        key_field="document_code",
        field_specs=(
            _field("document_code", "Document Code", required=True),
            _field("title", "Title", required=True),
            _field("document_structure_code", "Document Structure Code"),
            _field("business_version_label", "Business Version Label"),
            _field("file_name", "File Name"),
        ),
    ),
    _sheet(
        sheet_name="DocumentStructures",
        entity_label="Document Structures",
        owner_module_code="platform",
        description="Shared document taxonomy available to maintenance libraries and evidence.",
        key_field="structure_code",
        field_specs=(
            _field("structure_code", "Structure Code", required=True),
            _field("label", "Label", required=True),
            _field("parent_structure_code", "Parent Structure Code"),
            _field("status", "Status"),
        ),
    ),
    _sheet(
        sheet_name="DocumentLinks",
        entity_label="Maintenance Document Links",
        owner_module_code=MAINTENANCE_MODULE_CODE,
        description="Maintenance-owned links from assets, plans, work, and templates to shared documents.",
        key_field="link_ref",
        operation_key="maintenance_document_links",
        depends_on_sheets=("Documents", "DocumentStructures", "Assets", "PreventivePlans", "TaskTemplates"),
        field_specs=(
            _field("link_ref", "Link Ref", required=True),
            _field("owner_type", "Owner Type", required=True),
            _field("owner_code", "Owner Code", required=True),
            _field("document_code", "Document Code", required=True),
            _field("link_role", "Link Role"),
            _field("is_primary", "Is Primary"),
        ),
    ),
)


def maintenance_module_import_contracts() -> tuple[MaintenanceWorkbookSheetContract, ...]:
    return tuple(
        sheet
        for sheet in MAINTENANCE_WORKBOOK_SHEETS
        if sheet.owner_module_code == MAINTENANCE_MODULE_CODE and sheet.operation_key is not None
    )


def maintenance_reference_workbook_sheets() -> tuple[MaintenanceWorkbookSheetContract, ...]:
    return tuple(
        sheet
        for sheet in MAINTENANCE_WORKBOOK_SHEETS
        if sheet.owner_module_code != MAINTENANCE_MODULE_CODE or sheet.operation_key is None
    )


def maintenance_import_schemas() -> dict[str, tuple[ImportFieldSpec, ...]]:
    return {
        sheet.operation_key: sheet.field_specs
        for sheet in maintenance_module_import_contracts()
        if sheet.operation_key is not None
    }


__all__ = [
    "MAINTENANCE_MODULE_CODE",
    "MAINTENANCE_WORKBOOK_SHEETS",
    "MaintenanceWorkbookSheetContract",
    "maintenance_import_schemas",
    "maintenance_module_import_contracts",
    "maintenance_reference_workbook_sheets",
]
