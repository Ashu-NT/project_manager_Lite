from __future__ import annotations


def bind_task_facade_signals(
    facade,
    task_list,
    assignments_ctrl,
    dependencies_ctrl,
    time_ctrl,
    collab_ctrl,
) -> None:
    """Connect sub-controller signals to the facade's forwarded signals."""
    task_list.tasksTableModelChanged.connect(facade.tasksTableModelChanged)
    task_list.overviewChanged.connect(facade.overviewChanged)
    task_list.projectOptionsChanged.connect(facade.projectOptionsChanged)
    task_list.statusOptionsChanged.connect(facade.statusOptionsChanged)
    task_list.bulkStatusOptionsChanged.connect(facade.bulkStatusOptionsChanged)
    task_list.priorityOptionsChanged.connect(facade.priorityOptionsChanged)
    task_list.scheduleOptionsChanged.connect(facade.scheduleOptionsChanged)
    task_list.tasksChanged.connect(facade.tasksChanged)
    task_list.selectedTaskChanged.connect(facade.selectedTaskChanged)
    task_list.selectedTaskIdsChanged.connect(facade.selectedTaskIdsChanged)
    task_list.selectedTaskCountChanged.connect(facade.selectedTaskCountChanged)
    task_list.selectedTaskDoneCountChanged.connect(facade.selectedTaskDoneCountChanged)
    task_list.taskActionHistoryChanged.connect(facade.taskActionHistoryChanged)

    assignments_ctrl.assignmentOptionsChanged.connect(facade.assignmentOptionsChanged)
    assignments_ctrl.assignmentsChanged.connect(facade.assignmentsChanged)
    assignments_ctrl.assignmentPreviewChanged.connect(facade.assignmentPreviewChanged)
    assignments_ctrl.taskSkillRequirementsChanged.connect(facade.taskSkillRequirementsChanged)

    dependencies_ctrl.dependencyTaskOptionsChanged.connect(facade.dependencyTaskOptionsChanged)
    dependencies_ctrl.dependencyTypeOptionsChanged.connect(facade.dependencyTypeOptionsChanged)
    dependencies_ctrl.dependenciesChanged.connect(facade.dependenciesChanged)

    time_ctrl.timeAssignmentOptionsChanged.connect(facade.timeAssignmentOptionsChanged)
    time_ctrl.timePeriodOptionsChanged.connect(facade.timePeriodOptionsChanged)
    time_ctrl.timeAssignmentSummaryChanged.connect(facade.timeAssignmentSummaryChanged)
    time_ctrl.timeEntriesChanged.connect(facade.timeEntriesChanged)
    time_ctrl.selectedTimeEntryChanged.connect(facade.selectedTimeEntryChanged)

    collab_ctrl.collaborationMentionOptionsChanged.connect(facade.collaborationMentionOptionsChanged)
    collab_ctrl.collaborationDocumentOptionsChanged.connect(facade.collaborationDocumentOptionsChanged)
    collab_ctrl.collaborationCommentsChanged.connect(facade.collaborationCommentsChanged)
    collab_ctrl.collaborationPresenceChanged.connect(facade.collaborationPresenceChanged)

    facade.destroyed.connect(collab_ctrl.on_destroyed_cleanup)


__all__ = ["bind_task_facade_signals"]
