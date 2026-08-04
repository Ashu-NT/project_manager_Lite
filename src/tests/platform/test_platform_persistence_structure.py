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
}

FLAT_AREAS = {
    "auth",
    "departments",
    "documents",
    "employee",
    "enterprise_calendar",
    "identity",
    "modules",
    "notification",
    "org",
    "party",
    "platform_events",
    "runtime_tracking",
    "sites",
    "tenant",
    "time",
    "user_tenant",
}


def _source_file_stems(path: Path) -> set[str]:
    return {item.stem for item in path.glob("*.py") if not item.stem.startswith("_")}


def test_platform_persistence_uses_module_style_layout() -> None:
    source_dirs = {
        path.name
        for path in PERSISTENCE_ROOT.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }

    assert source_dirs == {"mappers", "orm", "repositories"}
    for area in ("orm", "repositories"):
        assert _source_file_stems(PERSISTENCE_ROOT / area) == FLAT_AREAS
        for nested_file in NESTED_AREA_FILES:
            assert (PERSISTENCE_ROOT / area / nested_file).exists()
    mapper_flat_areas = FLAT_AREAS - {"identity", "modules", "runtime_tracking"}
    assert _source_file_stems(PERSISTENCE_ROOT / "mappers") == mapper_flat_areas
    for nested_file in NESTED_AREA_FILES:
        assert (PERSISTENCE_ROOT / "mappers" / nested_file).exists()

