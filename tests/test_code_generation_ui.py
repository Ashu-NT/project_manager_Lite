from __future__ import annotations

from ui.modules.inventory_procurement.inventory.storeroom_dialogs import StoreroomEditDialog
from ui.modules.inventory_procurement.item_master.category_dialogs import InventoryItemCategoryEditDialog
from ui.modules.inventory_procurement.item_master.item_dialogs import InventoryItemEditDialog
from src.ui.platform.dialogs.admin.departments.dialogs import DepartmentEditDialog
from src.ui.platform.dialogs.admin.documents.dialogs import DocumentEditDialog
from src.ui.platform.dialogs.admin.employees.dialogs import EmployeeEditDialog
from src.ui.platform.dialogs.admin.organizations.dialogs import OrganizationEditDialog
from src.ui.platform.dialogs.admin.parties.dialogs import PartyEditDialog
from src.ui.platform.dialogs.admin.sites.dialogs import SiteEditDialog
from src.ui.shared.widgets.code_generation import CodeFieldWidget, suggest_generated_code


def test_suggest_generated_code_uses_uppercase_prefix_and_name_hint():
    code = suggest_generated_code("site", "Berlin Plant")

    assert code.startswith("SITE-BERL-")
    assert code == code.upper()
    assert len(code.split("-")[-1]) == 6


def test_entity_dialogs_offer_generate_buttons_for_code_fields(qapp):
    organization_dialog = OrganizationEditDialog()
    organization_dialog.display_name_edit.setText("Operations Hub")
    assert isinstance(organization_dialog.organization_code_field, CodeFieldWidget)
    organization_dialog.organization_code_field.generate_button.click()
    assert organization_dialog.organization_code.startswith("ORG-OPER-")

    site_dialog = SiteEditDialog()
    site_dialog.name_edit.setText("Berlin Plant")
    site_dialog.site_code_field.generate_button.click()
    assert site_dialog.site_code.startswith("SITE-BERL-")

    department_dialog = DepartmentEditDialog()
    department_dialog.name_edit.setText("Operations")
    department_dialog.department_code_field.generate_button.click()
    department_dialog.cost_center_code_field.generate_button.click()
    assert department_dialog.department_code.startswith("DEPT-OPER-")
    assert department_dialog.cost_center_code.startswith("CC-OPER-")

    party_dialog = PartyEditDialog()
    party_dialog.party_name_edit.setText("North Supply")
    party_dialog.party_code_field.generate_button.click()
    assert party_dialog.party_code.startswith("PARTY-NORT-")

    document_dialog = DocumentEditDialog()
    document_dialog.title_edit.setText("Pump Manual")
    document_dialog.document_code_field.generate_button.click()
    assert document_dialog.document_code.startswith("DOC-PUMP-")

    employee_dialog = EmployeeEditDialog()
    employee_dialog.full_name_edit.setText("Alex Example")
    employee_dialog.employee_code_field.generate_button.click()
    assert employee_dialog.employee_code.startswith("EMP-ALEX-")

    item_dialog = InventoryItemEditDialog()
    item_dialog.name_edit.setText("Portable Generator")
    item_dialog.item_code_field.generate_button.click()
    assert item_dialog.item_code.startswith("ITEM-PORT-")

    category_dialog = InventoryItemCategoryEditDialog()
    category_dialog.name_edit.setText("Maintenance Spares")
    category_dialog.category_code_field.generate_button.click()
    assert category_dialog.category_code.startswith("CAT-MAIN-")

    storeroom_dialog = StoreroomEditDialog(site_options=[("Main Site", "site-1")])
    storeroom_dialog.name_edit.setText("Central Stores")
    storeroom_dialog.storeroom_code_field.generate_button.click()
    assert storeroom_dialog.storeroom_code.startswith("STORE-CENT-")
