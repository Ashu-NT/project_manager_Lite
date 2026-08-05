from src.api.desktop.platform.models.access import (
    ScopedAccessGrantAssignCommand,
    ScopedAccessGrantDto,
    ScopedAccessGrantRemoveCommand,
    ScopeTargetDto,
    ScopeTypeChoiceDto,
)
from src.core.platform.api.desktop.approval.models.approval import (
    ApprovalDecisionCommand,
    ApprovalRequestDto,
)
from src.api.desktop.platform.models.calendar import (
    WorkingCalendarDayDto,
    WorkingCalendarHolidayCreateCommand,
    WorkingCalendarHolidayDto,
    WorkingCalendarOptionDto,
    WorkingCalendarSnapshotDto,
    WorkingCalendarUpdateCommand,
    WorkingDayCalculationCommand,
    WorkingDayCalculationDto,
)
from src.api.desktop.platform.models.common import DesktopApiError, DesktopApiResult
from src.core.platform.api.desktop.master_data.documents.models.document import (
    DocumentCreateCommand,
    DocumentDto,
    DocumentLinkCreateCommand,
    DocumentLinkDto,
    DocumentStructureCreateCommand,
    DocumentStructureDto,
    DocumentStructureUpdateCommand,
    DocumentUpdateCommand,
)
from src.core.platform.api.desktop.master_data.department.models.department import (
    DepartmentCreateCommand,
    DepartmentDto,
    DepartmentLocationReferenceDto,
    DepartmentUpdateCommand,
)
from src.core.platform.api.desktop.master_data.employee.models.employee import (
    EmployeeCreateCommand,
    EmployeeDto,
    EmployeeUpdateCommand,
)
from src.core.platform.api.desktop.security.identity.models.identity import (
    ApiKeyCredentialDto,
    ApiKeyIssueCommand,
    IssuedApiKeyDto,
    ServicePrincipalCreateCommand,
    ServicePrincipalDto,
)
from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationDto,
    OrganizationProvisionCommand,
    OrganizationUpdateCommand,
)
from src.core.platform.api.desktop.master_data.party.models.party import PartyCreateCommand, PartyDto, PartyUpdateCommand
from src.core.platform.api.desktop.platform_runtime.models.runtime import (
    ModuleDto,
    ModuleEntitlementDto,
    ModuleStatePatchCommand,
    PlatformCapabilityDto,
    PlatformRuntimeContextDto,
)
from src.core.platform.api.desktop.master_data.site.models.site import SiteCreateCommand, SiteDto, SiteUpdateCommand
from src.api.desktop.platform.models.support import (
    SupportBundleDto,
    SupportEventDto,
    SupportInstallLaunchDto,
    SupportPathsDto,
    SupportSettingsDto,
    SupportSettingsUpdateCommand,
    SupportUpdateStatusDto,
)
from src.api.desktop.platform.models.user import (
    RoleDto,
    UserCreateCommand,
    UserDto,
    UserPasswordResetCommand,
    UserUpdateCommand,
)
from src.core.platform.api.desktop.tenant.tenancy.models.tenant import TenantDto, TenantInvitationDto
from src.core.platform.domain.approval import ApprovalStatus

__all__ = [
    "ApiKeyCredentialDto",
    "ApiKeyIssueCommand",
    "ApprovalDecisionCommand",
    "ApprovalRequestDto",
    "ApprovalStatus",
    "WorkingCalendarDayDto",
    "WorkingCalendarHolidayCreateCommand",
    "WorkingCalendarHolidayDto",
    "WorkingCalendarOptionDto",
    "WorkingCalendarSnapshotDto",
    "WorkingCalendarUpdateCommand",
    "WorkingDayCalculationCommand",
    "WorkingDayCalculationDto",
    "DepartmentCreateCommand",
    "DepartmentDto",
    "DepartmentLocationReferenceDto",
    "DepartmentUpdateCommand",
    "DesktopApiError",
    "DesktopApiResult",
    "DocumentCreateCommand",
    "DocumentDto",
    "DocumentLinkCreateCommand",
    "DocumentLinkDto",
    "DocumentStructureCreateCommand",
    "DocumentStructureDto",
    "DocumentStructureUpdateCommand",
    "DocumentUpdateCommand",
    "EmployeeCreateCommand",
    "EmployeeDto",
    "EmployeeUpdateCommand",
    "IssuedApiKeyDto",
    "ModuleDto",
    "ModuleEntitlementDto",
    "ModuleStatePatchCommand",
    "OrganizationDto",
    "OrganizationProvisionCommand",
    "OrganizationUpdateCommand",
    "PartyCreateCommand",
    "PartyDto",
    "PartyUpdateCommand",
    "PlatformCapabilityDto",
    "PlatformRuntimeContextDto",
    "RoleDto",
    "ScopedAccessGrantAssignCommand",
    "ScopedAccessGrantDto",
    "ScopedAccessGrantRemoveCommand",
    "ScopeTargetDto",
    "ScopeTypeChoiceDto",
    "SiteCreateCommand",
    "SiteDto",
    "SiteUpdateCommand",
    "ServicePrincipalCreateCommand",
    "ServicePrincipalDto",
    "SupportBundleDto",
    "SupportEventDto",
    "SupportInstallLaunchDto",
    "SupportPathsDto",
    "SupportSettingsDto",
    "SupportSettingsUpdateCommand",
    "SupportUpdateStatusDto",
    "UserCreateCommand",
    "UserDto",
    "UserPasswordResetCommand",
    "UserUpdateCommand",
    "TenantDto",
    "TenantInvitationDto",
]
