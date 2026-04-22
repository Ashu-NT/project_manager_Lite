from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PERSISTENCE_ROOT = ROOT / "src" / "core" / "platform" / "infrastructure" / "persistence"
EXPECTED_AREAS = {
    "access",
    "approval",
    "audit",
    "auth",
    "documents",
    "modules",
    "org",
    "party",
    "runtime_tracking",
    "time",
}


def _source_file_stems(path: Path) -> set[str]:
    return {item.stem for item in path.glob("*.py") if item.stem != "__init__"}


def test_platform_persistence_uses_module_style_layout() -> None:
    source_dirs = {
        path.name
        for path in PERSISTENCE_ROOT.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }

    assert source_dirs == {"mappers", "orm", "repositories"}
    assert _source_file_stems(PERSISTENCE_ROOT / "orm") == EXPECTED_AREAS
    assert _source_file_stems(PERSISTENCE_ROOT / "repositories") == EXPECTED_AREAS
    assert _source_file_stems(PERSISTENCE_ROOT / "mappers") == EXPECTED_AREAS - {
        "modules",
        "runtime_tracking",
    }
