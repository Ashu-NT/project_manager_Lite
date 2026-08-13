from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT
PERSISTENCE_ROOT = ROOT / "src" / "core" / "platform" / "infrastructure" / "persistence"

# Areas already regrouped by content per the layer-first restructure (§5a) land as
# nested `<group>/<file>.py` in each of orm/repositories/mappers instead of a flat
# `<area>.py`. Update this set in lockstep as each remaining group's phase lands.
NESTED_AREA_FILES = {
    "history/activity/activity.py",
    "history/audit/audit_entry.py",
    "approval/approval.py",
    "events/notifications/notification.py",
    "events/platform_events/platform_events.py",
    "master_data/employee/employee.py",
    "master_data/site/sites.py",
    "master_data/department/departments.py",
    "master_data/org/org.py",
    "master_data/documents/documents.py",
    "master_data/party/party.py",
    "tenant/tenancy/tenant.py",
    "tenant/tenancy/user_tenant.py",
    "time_management/time/time.py",
    "time_management/calendar/enterprise_calendar.py",
    "security/auth/auth.py",
}

# runtime_tracking, modules, and identity have no mapper (never did — "no
# mapper exists today" per §8), so their nested files only need to exist
# under orm/ and repositories/, not mappers/.
NESTED_AREA_FILES_NO_MAPPER = {
    "data_operations/runtime_tracking/runtime_tracking.py",
    "tenant/modules/modules.py",
    "security/identity/identity.py",
}

FLAT_AREAS = set()


def _source_file_stems(path: Path) -> set[str]:
    return {item.stem for item in path.glob("*.py") if not item.stem.startswith("_")}


def test_platform_persistence_uses_module_style_layout() -> None:
    source_dirs = {
        path.name
        for path in PERSISTENCE_ROOT.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }

    assert source_dirs == {"mappers", "orm", "repositories", "read"}
    for area in ("orm", "repositories"):
        assert _source_file_stems(PERSISTENCE_ROOT / area) == FLAT_AREAS
        for nested_file in NESTED_AREA_FILES | NESTED_AREA_FILES_NO_MAPPER:
            assert (PERSISTENCE_ROOT / area / nested_file).exists()
    mapper_flat_areas = FLAT_AREAS
    assert _source_file_stems(PERSISTENCE_ROOT / "mappers") == mapper_flat_areas
    for nested_file in NESTED_AREA_FILES:
        assert (PERSISTENCE_ROOT / "mappers" / nested_file).exists()

