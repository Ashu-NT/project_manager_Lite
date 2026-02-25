from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_project_tab_has_professional_filters():
    tab_text = (ROOT / "ui" / "project" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    mixin_text = (ROOT / "ui" / "project" / "filtering.py").read_text(encoding="utf-8", errors="ignore")
    assert "from ui.project.filtering import ProjectFiltersMixin" in tab_text
    assert "self._build_project_filters(layout)" in tab_text
    assert "class ProjectFiltersMixin" in mixin_text
    assert 'self.project_search_filter.setPlaceholderText("Name, client, description...")' in mixin_text
    assert 'self.project_status_filter.addItem("All", userData="")' in mixin_text
    assert 'self.btn_clear_project_filters = QPushButton("Clear Filters")' in mixin_text


def test_resource_tab_has_professional_filters():
    tab_text = (ROOT / "ui" / "resource" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    mixin_text = (ROOT / "ui" / "resource" / "filtering.py").read_text(encoding="utf-8", errors="ignore")
    assert "from ui.resource.filtering import ResourceFiltersMixin" in tab_text
    assert "self._build_resource_filters(layout)" in tab_text
    assert "class ResourceFiltersMixin" in mixin_text
    assert 'self.resource_search_filter.setPlaceholderText("Name, role, category...")' in mixin_text
    assert 'self.resource_active_filter.addItem("Active", userData="active")' in mixin_text
    assert 'self.resource_category_filter.addItem("All", userData="")' in mixin_text
    assert 'self.btn_clear_resource_filters = QPushButton("Clear Filters")' in mixin_text


def test_task_tab_has_professional_filters_with_cached_refresh():
    tab_text = (ROOT / "ui" / "task" / "tab.py").read_text(encoding="utf-8", errors="ignore")
    mixin_text = (ROOT / "ui" / "task" / "filtering.py").read_text(encoding="utf-8", errors="ignore")
    flow_text = (ROOT / "ui" / "task" / "project_flow.py").read_text(encoding="utf-8", errors="ignore")
    assert "from ui.task.filtering import TaskFiltersMixin" in tab_text
    assert "self._build_task_filters(root)" in tab_text
    assert "class TaskFiltersMixin" in mixin_text
    assert "self.task_status_filter = QComboBox()" in mixin_text
    assert "self.task_progress_filter" not in mixin_text
    assert "def _refresh_tasks_from_cache" in flow_text
    assert "visible_tasks = self._apply_task_filters(list(self._all_tasks))" in flow_text
