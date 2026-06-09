from __future__ import annotations


def export_register(controller) -> None:
    controller._set_error_message("")
    controller._set_feedback_message(
        "Export is not available here. Open the Reports section to generate register entries,"
        " risk summaries, and issue logs."
    )


__all__ = ["export_register"]
