
""" Track changes in  project, tasks, baseline, report updates dashboard"""
from PySide6.QtCore import QObject, Signal


class DomainEvents(QObject):
    project_changed = Signal(str)   # project_id
    tasks_changed = Signal(str)     # project_id
    costs_changed = Signal(str)     # project_id
    baseline_changed = Signal(str)  # project_id


# SINGLE global instance
domain_events = DomainEvents()
