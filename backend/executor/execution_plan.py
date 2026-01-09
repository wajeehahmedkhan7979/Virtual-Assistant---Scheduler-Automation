"""
Execution plan structures and audit trail.
Represents a planned sequence of actions without executing them.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ExecutionDecision(str, Enum):
    """Decision status for an action."""
    APPROVED = "approved"
    BLOCKED = "blocked"
    REQUIRES_APPROVAL = "requires_approval"
    SIMULATED = "simulated"


@dataclass
class ExecutionStep:
    """
    A single planned action step.
    
    Attributes:
        action: The action specification (type, priority, etc.)
        decision: The eligibility decision (approved, blocked, etc.)
        reasoning: Why the decision was made
        is_simulated: Whether this is a simulation
    """
    action: Dict[str, Any]
    decision: ExecutionDecision
    reasoning: str
    is_simulated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action": self.action,
            "decision": self.decision.value,
            "reasoning": self.reasoning,
            "is_simulated": self.is_simulated,
        }


@dataclass
class ExecutionPlan:
    """
    A plan to execute a set of actions.
    
    This structure represents what WOULD happen if actions are executed,
    but does NOT actually execute them.
    
    Attributes:
        recommendation_id: The ActionRecommendation ID
        user_id: User ID for audit trail
        email_job_id: EmailJob ID for audit trail
        steps: List of planned execution steps
        created_at: When plan was created
        is_simulated: Whether plan is in simulation mode
        status: Plan status (planned, simulated, executed, blocked)
        reasoning: Overall reasoning for the plan
    """
    recommendation_id: str
    user_id: str
    email_job_id: str
    steps: List[ExecutionStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_simulated: bool = True
    status: str = "planned"
    reasoning: str = ""
    
    def add_step(
        self,
        action: Dict[str, Any],
        decision: ExecutionDecision,
        reasoning: str,
    ) -> None:
        """
        Add a step to the execution plan.
        
        Args:
            action: Action specification
            decision: Eligibility decision
            reasoning: Reasoning for the decision
        """
        step = ExecutionStep(
            action=action,
            decision=decision,
            reasoning=reasoning,
            is_simulated=self.is_simulated,
        )
        self.steps.append(step)
    
    def get_approved_actions(self) -> List[Dict[str, Any]]:
        """
        Get all approved actions from the plan.
        
        Returns:
            List of approved action specifications
        """
        return [
            step.action
            for step in self.steps
            if step.decision == ExecutionDecision.APPROVED
        ]
    
    def get_blocked_actions(self) -> List[Dict[str, Any]]:
        """
        Get all blocked actions from the plan.
        
        Returns:
            List of blocked action specifications
        """
        return [
            step.action
            for step in self.steps
            if step.decision == ExecutionDecision.BLOCKED
        ]
    
    def summary(self) -> str:
        """
        Generate a human-readable summary of the plan.
        
        Returns:
            Summary string
        """
        approved_count = len(self.get_approved_actions())
        blocked_count = len(self.get_blocked_actions())
        
        summary = (
            f"ExecutionPlan for recommendation {self.recommendation_id}\n"
            f"  Approved: {approved_count} actions\n"
            f"  Blocked: {blocked_count} actions\n"
            f"  Status: {self.status}\n"
            f"  Simulated: {self.is_simulated}\n"
        )
        
        if self.reasoning:
            summary += f"  Reasoning: {self.reasoning}\n"
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "recommendation_id": self.recommendation_id,
            "user_id": self.user_id,
            "email_job_id": self.email_job_id,
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at.isoformat(),
            "is_simulated": self.is_simulated,
            "status": self.status,
            "reasoning": self.reasoning,
        }
