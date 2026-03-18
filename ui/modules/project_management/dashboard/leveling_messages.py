from __future__ import annotations


def format_auto_level_result_message(result) -> str:
    resolved = max(0, int(result.conflicts_before) - int(result.conflicts_after))
    message = (
        f"Conflicts: {result.conflicts_before} -> {result.conflicts_after} "
        f"(resolved {resolved})\n"
        f"Iterations used: {result.iterations}\n"
        f"Tasks shifted: {len(result.actions)}"
    )
    if result.actions:
        sample = result.actions[:6]
        changes = "\n".join(
            f"- {action.task_name}: {action.old_start} -> {action.new_start} | {action.old_end} -> {action.new_end}"
            for action in sample
        )
        if len(result.actions) > len(sample):
            changes += f"\n- ... and {len(result.actions) - len(sample)} more shift(s)"
        return f"{message}\n\nDate shifts:\n{changes}"
    return (
        message
        + "\n\nNo eligible task was shifted. Auto-level only moves tasks that:"
        + "\n- have no successors"
        + "\n- have no actual start/end"
        + "\n- are not already in progress"
    )


__all__ = ["format_auto_level_result_message"]
