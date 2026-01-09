"""
Action Executor: scaffolding for action execution.

This module provides decision-making and planning for actions based on
ActionRecommendation objects. It does NOT execute actions; it only:
  - Validates action specifications
  - Decides eligibility (approved / blocked / requires approval)
  - Creates structured execution plans
  - Logs and audits all decisions

Actual execution (calling Gmail API, etc.) is deferred to a future phase.
"""
from typing import Dict, Any, List, Optional
import logging

from backend.executor.allowed_actions import (
    is_action_type_allowed,
    get_required_fields,
    ACTION_OPTIONAL_FIELDS,
)
from backend.executor.execution_plan import (
    ExecutionPlan,
    ExecutionDecision,
)


logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Executor for action recommendations.
    
    Responsible for:
    - Validating actions against allowed types and schema
    - Deciding eligibility based on safety rules
    - Planning execution sequences
    - Generating audit trails
    
    Does NOT:
    - Call external APIs
    - Modify inbox state
    - Send emails
    - Execute side effects
    """
    
    def __init__(self, simulation_mode: bool = True):
        """
        Initialize ActionExecutor.
        
        Args:
            simulation_mode: If True, all plans are marked as simulated.
                           Used for testing and dry-runs.
        """
        self.simulation_mode = simulation_mode
        self.logger = logger
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """
        Validate action specification.
        
        Checks:
        - Action type is allowed
        - Required fields are present
        - No invalid fields
        
        Args:
            action: Action specification dict
        
        Returns:
            True if valid, False otherwise
        """
        if not action:
            self.logger.warning("validate_action: empty action")
            return False
        
        # Check if type field exists
        if "type" not in action:
            self.logger.warning("validate_action: missing 'type' field")
            return False
        
        action_type = action["type"]
        
        # Check if action type is allowed
        if not is_action_type_allowed(action_type):
            self.logger.warning(
                f"validate_action: action type '{action_type}' not allowed"
            )
            return False
        
        # Check required fields
        required_fields = get_required_fields(action_type)
        for field in required_fields:
            if field not in action:
                self.logger.warning(
                    f"validate_action: missing required field '{field}' "
                    f"for action type '{action_type}'"
                )
                return False
        
        return True
    
    def decide_eligibility(self, action: Dict[str, Any]) -> ExecutionDecision:
        """
        Decide eligibility of an action.
        
        Currently:
        - All validated, allowed actions are APPROVED
        - Invalid or unsupported actions are BLOCKED
        
        Future: Could add logic for:
        - User preferences
        - Risk scoring
        - Approval thresholds
        
        Args:
            action: Action specification dict
        
        Returns:
            ExecutionDecision (APPROVED, BLOCKED, REQUIRES_APPROVAL)
        """
        if not self.validate_action(action):
            return ExecutionDecision.BLOCKED
        
        # All valid allowed actions are approved in this phase
        return ExecutionDecision.APPROVED
    
    def plan_execution(
        self,
        recommendation: Any,
        actions: List[Dict[str, Any]],
    ) -> ExecutionPlan:
        """
        Create an execution plan for a set of actions.
        
        Does NOT execute actions; only creates a plan and logs decisions.
        
        Args:
            recommendation: ActionRecommendation object
            actions: List of action specifications to plan
        
        Returns:
            ExecutionPlan object containing decisions and reasoning
        """
        plan = ExecutionPlan(
            recommendation_id=recommendation.id,
            user_id=recommendation.user_id,
            email_job_id=recommendation.email_job_id,
            is_simulated=self.simulation_mode,
            status="simulated" if self.simulation_mode else "planned",
            reasoning=self._generate_reasoning(recommendation, actions),
        )
        
        # Evaluate each action
        for action in actions:
            decision = self.decide_eligibility(action)
            reasoning = self._generate_step_reasoning(action, decision)
            
            plan.add_step(action, decision, reasoning)
            
            # Log each decision
            self.logger.info(
                f"Action eligibility: {action.get('type')} -> {decision.value} "
                f"(rec={recommendation.id})"
            )
        
        # Log plan creation
        self.logger.info(
            f"ExecutionPlan created for recommendation {recommendation.id}: "
            f"{len(plan.get_approved_actions())} approved, "
            f"{len(plan.get_blocked_actions())} blocked"
        )
        
        return plan
    
    def _generate_reasoning(
        self,
        recommendation: Any,
        actions: List[Dict[str, Any]],
    ) -> str:
        """
        Generate overall reasoning for an execution plan.
        
        Args:
            recommendation: ActionRecommendation object
            actions: List of actions
        
        Returns:
            Reasoning string
        """
        import json
        
        num_actions = len(actions)
        sim_marker = "[SIMULATION] " if self.simulation_mode else ""
        
        # Handle rule_names that might be JSON string or list
        rule_names = recommendation.rule_names
        if isinstance(rule_names, str):
            try:
                rule_names = json.loads(rule_names)
            except (json.JSONDecodeError, TypeError):
                rule_names = [rule_names]
        
        if not isinstance(rule_names, list):
            rule_names = [str(rule_names)]
        
        reasoning = (
            f"{sim_marker}Plan for {num_actions} recommended action(s) "
            f"based on rules: {rule_names}. "
            f"Confidence: {recommendation.confidence_score}/100"
        )
        
        return reasoning
    
    def _generate_step_reasoning(
        self,
        action: Dict[str, Any],
        decision: ExecutionDecision,
    ) -> str:
        """
        Generate reasoning for a single action decision.
        
        Args:
            action: Action specification
            decision: Eligibility decision
        
        Returns:
            Reasoning string
        """
        action_type = action.get("type", "unknown")
        
        if decision == ExecutionDecision.APPROVED:
            priority = action.get("priority", "default")
            reason = action.get("reason", "")
            detail = f" (priority={priority})" if priority else ""
            return f"Action '{action_type}' is allowed and approved{detail}"
        
        elif decision == ExecutionDecision.BLOCKED:
            if not is_action_type_allowed(action_type):
                return (
                    f"Action type '{action_type}' is not in allowed list. "
                    f"Blocked for safety."
                )
            else:
                return f"Action '{action_type}' failed validation. Blocked."
        
        elif decision == ExecutionDecision.REQUIRES_APPROVAL:
            return f"Action '{action_type}' requires manual approval."
        
        else:
            return f"Action '{action_type}' decision: {decision.value}"
    
    def log_plan(self, plan: ExecutionPlan) -> None:
        """
        Log an execution plan to audit trail.
        
        Args:
            plan: ExecutionPlan object
        """
        self.logger.info(f"\n{plan.summary()}")
