from __future__ import annotations


def set_overview(controller, overview: dict) -> None:
    if overview == controller._overview:
        return
    controller._overview = overview
    controller.overviewChanged.emit()


def set_queue_state(controller, state: dict) -> None:
    if state == controller._queue_state:
        return
    controller._queue_state = state
    controller.queueStateChanged.emit()


def set_plan_library_state(controller, state: dict) -> None:
    if state == controller._plan_library_state:
        return
    controller._plan_library_state = state
    controller.planLibraryStateChanged.emit()


def set_template_library_state(controller, state: dict) -> None:
    if state == controller._template_library_state:
        return
    controller._template_library_state = state
    controller.templateLibraryStateChanged.emit()


def set_plan_form_options(controller, options: dict) -> None:
    if options == controller._plan_form_options:
        return
    controller._plan_form_options = options
    controller.planFormOptionsChanged.emit()


def set_plan_task_form_options(controller, options: dict) -> None:
    if options == controller._plan_task_form_options:
        return
    controller._plan_task_form_options = options
    controller.planTaskFormOptionsChanged.emit()


def set_template_form_options(controller, options: dict) -> None:
    if options == controller._template_form_options:
        return
    controller._template_form_options = options
    controller.templateFormOptionsChanged.emit()


def set_step_form_options(controller, options: dict) -> None:
    if options == controller._step_form_options:
        return
    controller._step_form_options = options
    controller.stepFormOptionsChanged.emit()
