from __future__ import annotations

import inspect

import pytest

from src.core.modules.maintenance.application.assets.asset_service import (
    MaintenanceAssetService,
)
from src.core.modules.maintenance.application.assets.component_service import (
    MaintenanceAssetComponentService,
)
from src.core.modules.maintenance.application.assets.location_service import (
    MaintenanceLocationService,
)
from src.core.modules.maintenance.application.assets.system_service import (
    MaintenanceSystemService,
)
from src.core.modules.maintenance.application.documents.document_service import (
    MaintenanceDocumentService,
)
from src.core.modules.maintenance.application.preventive.services.generation_service import (
    MaintenancePreventiveGenerationService,
)
from src.core.modules.maintenance.application.preventive.services.plan_service import (
    MaintenancePreventivePlanService,
)
from src.core.modules.maintenance.application.preventive.services.plan_task_service import (
    MaintenancePreventivePlanTaskService,
)
from src.core.modules.maintenance.application.preventive.services.task_step_template_service import (
    MaintenanceTaskStepTemplateService,
)
from src.core.modules.maintenance.application.preventive.services.task_template_service import (
    MaintenanceTaskTemplateService,
)
from src.core.modules.maintenance.application.reliability.downtime_event_service import (
    MaintenanceDowntimeEventService,
)
from src.core.modules.maintenance.application.reliability.failure_code_service import (
    MaintenanceFailureCodeService,
)
from src.core.modules.maintenance.application.reliability.integration_source_service import (
    MaintenanceIntegrationSourceService,
)
from src.core.modules.maintenance.application.reliability.reliability_service import (
    MaintenanceReliabilityService,
)
from src.core.modules.maintenance.application.reliability.sensor_exception_service import (
    MaintenanceSensorExceptionService,
)
from src.core.modules.maintenance.application.reliability.sensor_reading_service import (
    MaintenanceSensorReadingService,
)
from src.core.modules.maintenance.application.reliability.sensor_service import (
    MaintenanceSensorService,
)
from src.core.modules.maintenance.application.reliability.sensor_source_mapping_service import (
    MaintenanceSensorSourceMappingService,
)
from src.core.modules.maintenance.application.work_orders.labor_adapters import (
    MaintenanceTaskWorkAllocationRepository,
)
from src.core.modules.maintenance.application.work_orders.work_order_material_requirement_service import (
    MaintenanceWorkOrderMaterialRequirementService,
)
from src.core.modules.maintenance.application.work_orders.work_order_service import (
    MaintenanceWorkOrderService,
)
from src.core.modules.maintenance.application.work_orders.work_order_task_service import (
    MaintenanceWorkOrderTaskService,
)
from src.core.modules.maintenance.application.work_orders.work_order_task_step_service import (
    MaintenanceWorkOrderTaskStepService,
)
from src.core.modules.maintenance.application.work_requests.work_request_service import (
    MaintenanceWorkRequestService,
)
from src.core.modules.maintenance.infrastructure.reporting.service import (
    MaintenanceReportingService,
)
from src.core.platform.common.exceptions import BusinessRuleError


def _construct_without_tenant_context(cls):
    signature = inspect.signature(cls.__init__)
    positional_args = []
    keyword_args = {}
    for name, parameter in list(signature.parameters.items())[1:]:
        if name == "tenant_context_service":
            keyword_args[name] = None
            continue
        if parameter.default is not inspect._empty:
            continue
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional_args.append(object())
            continue
        if parameter.kind == inspect.Parameter.KEYWORD_ONLY:
            keyword_args[name] = object()
            continue
        raise AssertionError(f"Unsupported constructor parameter shape: {cls.__name__}.{name}")
    return cls(*positional_args, **keyword_args)


@pytest.mark.parametrize(
    "service_cls",
    [
        MaintenanceAssetService,
        MaintenanceAssetComponentService,
        MaintenanceLocationService,
        MaintenanceSystemService,
        MaintenanceDocumentService,
        MaintenancePreventiveGenerationService,
        MaintenancePreventivePlanService,
        MaintenancePreventivePlanTaskService,
        MaintenanceTaskStepTemplateService,
        MaintenanceTaskTemplateService,
        MaintenanceDowntimeEventService,
        MaintenanceFailureCodeService,
        MaintenanceIntegrationSourceService,
        MaintenanceReliabilityService,
        MaintenanceSensorExceptionService,
        MaintenanceSensorReadingService,
        MaintenanceSensorService,
        MaintenanceSensorSourceMappingService,
        MaintenanceTaskWorkAllocationRepository,
        MaintenanceWorkOrderMaterialRequirementService,
        MaintenanceWorkOrderService,
        MaintenanceWorkOrderTaskService,
        MaintenanceWorkOrderTaskStepService,
        MaintenanceWorkRequestService,
        MaintenanceReportingService,
    ],
)
def test_maintenance_services_require_tenant_context_service(service_cls) -> None:
    with pytest.raises(
        BusinessRuleError,
        match=rf"{service_cls.__name__} requires TenantContextService",
    ):
        _construct_without_tenant_context(service_cls)
