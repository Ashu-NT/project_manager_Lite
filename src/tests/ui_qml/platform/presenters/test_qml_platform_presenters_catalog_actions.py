from __future__ import annotations

from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.tests.platform._platform_test_helpers import build_connected_platform_registry


def test_platform_workspace_catalog_runs_control_and_settings_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    approve_result = catalog.approveRequestWithNote("approval-1", "Budget aligned with governance.")
    enable_result = catalog.toggleModuleEnabled("inventory_procurement")
    lifecycle_result = catalog.changeModuleLifecycleStatus("project_management", "suspended")

    assert approve_result == {"ok": True, "category": "", "code": "", "message": "Approval request approved and applied."}
    assert enable_result == {"ok": True, "category": "", "code": "", "message": "Module runtime state updated."}
    assert lifecycle_result == {"ok": True, "category": "", "code": "", "message": "Module lifecycle status updated."}

    approval_queue = catalog.approvalQueue()
    settings_overview = catalog.settingsOverview()
    module_entitlements = catalog.moduleEntitlements()
    project_management = {item["id"]: item for item in module_entitlements["items"]}["project_management"]
    inventory = {item["id"]: item for item in module_entitlements["items"]}["inventory_procurement"]

    assert approval_queue["items"][0]["statusLabel"] == "Approved"
    assert approval_queue["items"][0]["canPrimaryAction"] is False
    assert approval_queue["items"][0]["state"]["decisionNote"] == "Budget aligned with governance."
    assert "Decision note: Budget aligned with governance." in approval_queue["items"][0]["metaText"]
    assert settings_overview["metrics"][1]["value"] == "1"
    assert inventory["subtitle"].endswith("Enabled")
    assert project_management["statusLabel"] == "Suspended"
    assert project_management["state"]["runtimeEnabled"] is False
    assert project_management["canSecondaryAction"] is False
    assert catalog.controlWorkspace.feedbackMessage == "Approval request approved and applied."
    assert catalog.settingsWorkspace.feedbackMessage == "Module lifecycle status updated."
    assert catalog.settingsWorkspace.errorMessage == ""


def test_platform_workspace_catalog_runs_support_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    support_workspace = catalog.adminSupportWorkspace
    support_workspace.refresh()
    save_result = support_workspace.saveSettings(
        {
            "updateChannel": "beta",
            "updateAutoCheck": True,
            "updateManifestSource": "https://example.com/releases/beta-manifest.json",
        }
    )
    check_result = support_workspace.checkForUpdates(
        {
            "updateChannel": "beta",
            "updateAutoCheck": True,
            "updateManifestSource": "https://example.com/releases/beta-manifest.json",
        }
    )
    diagnostics_result = support_workspace.exportDiagnosticsTo("C:/pm/data/custom_support_diagnostics.zip")
    report_result = support_workspace.reportIncident()
    install_result = support_workspace.installAvailableUpdate(
        {
            "updateChannel": "beta",
            "updateAutoCheck": True,
            "updateManifestSource": "https://example.com/releases/beta-manifest.json",
        }
    )

    assert save_result == {"ok": True, "category": "", "code": "", "message": "Support settings saved."}
    assert check_result == {"ok": True, "category": "", "code": "", "message": "Update check completed."}
    assert diagnostics_result == {"ok": True, "category": "", "code": "", "message": "Diagnostics bundle created."}
    assert report_result == {"ok": True, "category": "", "code": "", "message": "Incident report package created."}
    assert install_result == {"ok": True, "category": "", "code": "", "message": "Update install handoff launched."}

    assert support_workspace.supportSettings["updateChannel"] == "beta"
    assert support_workspace.supportSettings["updateAutoCheck"] is True
    assert support_workspace.updateStatus["statusLabel"] == "Update Available"
    assert support_workspace.updateStatus["latestVersion"] == "1.2.0"
    assert support_workspace.bundleState["lastDiagnosticsPath"] == "C:/pm/data/custom_support_diagnostics.zip"
    assert support_workspace.bundleState["lastIncidentReportPath"].endswith(".zip")
    assert support_workspace.bundleState["supportEmail"] == "support@example.com"
    assert support_workspace.activityFeed["items"][0]["title"] == "Update handoff launched; app will close."
    assert support_workspace.feedbackMessage == "Update install handoff launched."
    assert support_workspace.errorMessage == ""


def test_platform_workspace_controllers_store_validation_errors() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())

    result = catalog.toggleModuleLicensed("hr_management")

    assert result["ok"] is False
    assert result["category"] == "validation"
    assert "planned" in result["message"].lower()
    assert "planned" in catalog.settingsWorkspace.errorMessage.lower()


def test_platform_workspace_catalog_runs_access_security_actions() -> None:
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=build_connected_platform_registry())
    catalog.adminAccessWorkspace.refresh()

    catalog.adminAccessWorkspace.setScopeType("site")
    assign_result = catalog.adminAccessWorkspace.assignMembership()
    remove_result = catalog.adminAccessWorkspace.removeMembership("user-2")
    unlock_result = catalog.adminAccessWorkspace.unlockUser("user-2")
    revoke_result = catalog.adminAccessWorkspace.revokeSessions("user-2")

    assert assign_result == {"ok": True, "category": "", "code": "", "message": "Access grant assigned."}
    assert remove_result == {"ok": True, "category": "", "code": "", "message": "Access grant removed."}
    assert unlock_result == {"ok": True, "category": "", "code": "", "message": "User account unlocked."}
    assert revoke_result == {"ok": True, "category": "", "code": "", "message": "User sessions revoked."}

    grants = catalog.adminAccessWorkspace.scopeGrants
    security_users = {item["id"]: item for item in catalog.adminAccessWorkspace.securityUsers["items"]}

    assert [item["title"] for item in grants["items"]] == ["Ada Lovelace"]
    assert security_users["user-2"]["statusLabel"] == "Inactive"
    assert catalog.adminAccessWorkspace.feedbackMessage == "User sessions revoked."
