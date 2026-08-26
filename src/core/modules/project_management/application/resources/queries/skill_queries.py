"""Skill and certification query methods for ResourceService."""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.contracts.reads.resources import (
    ResourceCapabilityReader,
    ResourceCertificationReadPage,
    ResourceSkillReadPage,
)

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class SkillQueryMixin:
    _resource_capability_reader: ResourceCapabilityReader | None

    def _capability_scope(self, operation_label: str):
        if self._tenant_context_service is None:
            raise RuntimeError("Resource capability reader scope is not configured.")
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    def query_resource_skills_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        proficiency: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "skillName",
        sort_direction: str = "asc",
    ) -> ResourceSkillReadPage:
        require_permission(
            self._user_session, "resource.read", operation_label="view resource skills"
        )
        if self._resource_capability_reader is None:
            raise RuntimeError("Resource capability reader is not configured.")
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={"skillName", "skillCode", "proficiency", "notes"},
            default_key="skillName",
        )
        normalized_proficiency = str(proficiency or "").strip().lower() or None
        if normalized_proficiency not in {
            None, "beginner", "intermediate", "advanced", "expert"
        }:
            normalized_proficiency = None
        scope = self._capability_scope("view resource skills")
        kwargs = dict(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            resource_id=str(resource_id or "").strip(),
            search_text=str(search_text or "").strip(),
            proficiency=normalized_proficiency,
            page=request.page,
            page_size=request.page_size,
            sort=sort,
        )
        result = self._resource_capability_reader.read_skills_page(**kwargs)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.filtered_total
        )
        if normalized_page != result.page:
            kwargs["page"] = normalized_page
            result = self._resource_capability_reader.read_skills_page(**kwargs)
        return result

    def query_resource_certifications_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "certificationName",
        sort_direction: str = "asc",
    ) -> ResourceCertificationReadPage:
        require_permission(
            self._user_session,
            "resource.read",
            operation_label="view resource certifications",
        )
        if self._resource_capability_reader is None:
            raise RuntimeError("Resource capability reader is not configured.")
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "certificationName", "certificationCode", "statusLabel",
                "issuedDate", "expiryDate", "issuer",
            },
            default_key="certificationName",
        )
        normalized_status = str(status or "").strip().lower() or None
        if normalized_status not in {
            None, "no-expiry", "valid", "expiring-soon", "expired"
        }:
            normalized_status = None
        scope = self._capability_scope("view resource certifications")
        kwargs = dict(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            resource_id=str(resource_id or "").strip(),
            search_text=str(search_text or "").strip(),
            status=normalized_status,
            as_of=date.today(),
            page=request.page,
            page_size=request.page_size,
            sort=sort,
        )
        result = self._resource_capability_reader.read_certifications_page(**kwargs)
        normalized_page = normalize_page_for_total(
            page=result.page, page_size=result.page_size, total=result.filtered_total
        )
        if normalized_page != result.page:
            kwargs["page"] = normalized_page
            result = self._resource_capability_reader.read_certifications_page(**kwargs)
        return result

__all__ = ["SkillQueryMixin"]
