"""PM-owned reviewer permissions for governed Approval request types."""

PM_APPROVAL_REVIEW_PERMISSIONS = {
    "baseline.create": "baseline.approve",
    "dependency.add": "task.approve",
    "dependency.remove": "task.approve",
    "dependency.update": "task.approve",
    "task.constraint.update": "task.approve",
    "scheduling.leveling.apply": "task.approve",
    "budget.approve": "budget.approve",
    "forecast.approve": "forecast.approve",
    "project_cost.approve": "project_cost.approve",
    "financial_change.apply": "financial_change.approve",
    "project_billing_preparation.approve": "billing_preparation.approve",
}


def pm_reviewer_permission(request_type: str) -> str:
    return PM_APPROVAL_REVIEW_PERMISSIONS[request_type]
