"""
Action Executor package.

Provides decision-making and planning for email actions without executing them.
"""

from .action_executor import ActionExecutor, ExecutionDecision
from .execution_plan import ExecutionPlan, ExecutionStep
from .allowed_actions import ALLOWED_ACTIONS

__all__ = [
    "ActionExecutor",
    "ExecutionDecision",
    "ExecutionPlan",
    "ExecutionStep",
    "ALLOWED_ACTIONS",
]
