from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError
from tests.ui_runtime_helpers import login_as


def test_master_data_exchange_service_imports_and_exports_shared_sites_and_parties(services, tmp_path):
    service = services["master_data_exchange_service"]

    sites_csv = tmp_path / "sites-import.csv"
    sites_csv.write_text(
        "site_code,name,city,currency_code,is_active\n"
        "HUB,Hamburg Hub,Hamburg,EUR,true\n",
        encoding="utf-8",
    )
    preview = service.preview_csv("sites", sites_csv)
    summary = service.import_csv("sites", sites_csv)
    site_artifact = service.export_csv("sites", tmp_path / "sites-export.csv", active_only=True)
    site_export_text = site_artifact.file_path.read_text(encoding="utf-8")

    parties_csv = tmp_path / "parties-import.csv"
    parties_csv.write_text(
        "party_code,party_name,party_type,country,is_active\n"
        "SUP-HUB,Hamburg Supply,SUPPLIER,Germany,true\n",
        encoding="utf-8",
    )
    preview_parties = service.preview_csv("parties", parties_csv)
    summary_parties = service.import_csv("parties", parties_csv)
    party_artifact = service.export_csv("parties", tmp_path / "parties-export.csv", active_only=True)
    party_export_text = party_artifact.file_path.read_text(encoding="utf-8")

    assert preview.created_count == 1
    assert summary.created_count == 1
    assert "HUB" in site_export_text
    assert preview_parties.created_count == 1
    assert summary_parties.created_count == 1
    assert "SUP-HUB" in party_export_text


def test_master_data_exchange_service_requires_settings_manage_for_imports(services, tmp_path):
    auth = services["auth_service"]
    auth.register_user("inventory-master-export", "StrongPass123", role_names=["inventory_manager"])
    login_as(services, "inventory-master-export", "StrongPass123")

    service = services["master_data_exchange_service"]
    csv_path = tmp_path / "sites-import.csv"
    csv_path.write_text(
        "site_code,name,currency_code\n"
        "BER,Berlin Hub,EUR\n",
        encoding="utf-8",
    )

    artifact = service.export_csv("sites", tmp_path / "sites-export.csv", active_only=True)
    assert artifact.file_path.exists()

    try:
        service.import_csv("sites", csv_path)
    except BusinessRuleError as exc:
        assert "settings.manage" in str(exc)
    else:
        raise AssertionError("Expected shared master import to require settings.manage.")
