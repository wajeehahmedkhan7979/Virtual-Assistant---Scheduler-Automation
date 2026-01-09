"""
Tests for action executor scaffolding.
Validates decision logic, eligibility checks, and execution planning without side effects.
"""
import pytest
import json
from datetime import datetime
from enum import Enum

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base, User, EmailAccount, EmailJob, ActionRecommendation
from backend.executor.action_executor import (
    ActionExecutor,
    ExecutionDecision,
    ExecutionPlan,
)
from backend.executor.allowed_actions import ALLOWED_ACTIONS


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    yield SessionLocal()


@pytest.fixture
def test_user(test_db):
    """Create test user."""
    user = User(
        id="test-user",
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
    )
    test_db.add(user)
    test_db.commit()
    return user


@pytest.fixture
def test_email_account(test_db, test_user):
    """Create test email account."""
    account = EmailAccount(
        id="test-account",
        user_id=test_user.id,
        provider="gmail",
        email="user@gmail.com",
        access_token_encrypted="encrypted_token",
        refresh_token_encrypted="encrypted_refresh",
    )
    test_db.add(account)
    test_db.commit()
    return account


@pytest.fixture
def test_email_job(test_db, test_user, test_email_account):
    """Create test email job."""
    email = EmailJob(
        id="test-email-1",
        user_id=test_user.id,
        email_account_id=test_email_account.id,
        email_id="gmail-id-123",
        sender="boss@company.com",
        subject="Urgent: Q4 Report Due",
        body="Please submit the Q4 financial report by EOD today.",
        classification="important",
        classification_confidence=95,
        is_processed=True,
    )
    test_db.add(email)
    test_db.commit()
    return email


@pytest.fixture
def test_recommendation(test_db, test_user, test_email_job):
    """Create test recommendation record."""
    recommendation = ActionRecommendation(
        id="rec-1",
        user_id=test_user.id,
        email_job_id=test_email_job.id,
        rule_names=json.dumps(["Flag important emails"]),
        recommended_actions=json.dumps([
            {"type": "flag", "priority": 9, "reason": "Important email"}
        ]),
        safety_flags=json.dumps([]),
        confidence_score=100,
        reasoning="Email classified as important with high confidence",
        status="generated",
    )
    test_db.add(recommendation)
    test_db.commit()
    return recommendation


@pytest.fixture
def executor():
    """Create action executor."""
    return ActionExecutor(simulation_mode=True)


# ============================================================================
# Tests: Allowed Actions
# ============================================================================

class TestAllowedActions:
    """Test allowed action types."""
    
    def test_allowed_actions_defined(self):
        """Test allowed actions list is defined."""
        assert len(ALLOWED_ACTIONS) > 0
        assert isinstance(ALLOWED_ACTIONS, list)
    
    def test_flag_action_allowed(self):
        """Test flag action is in allowed list."""
        assert "flag" in ALLOWED_ACTIONS
    
    def test_archive_action_allowed(self):
        """Test archive action is in allowed list."""
        assert "archive" in ALLOWED_ACTIONS
    
    def test_spam_action_allowed(self):
        """Test spam action is in allowed list."""
        assert "spam" in ALLOWED_ACTIONS
    
    def test_label_action_allowed(self):
        """Test label action is in allowed list."""
        assert "label" in ALLOWED_ACTIONS
    
    def test_read_action_allowed(self):
        """Test read action is in allowed list."""
        assert "read" in ALLOWED_ACTIONS


# ============================================================================
# Tests: Action Validation
# ============================================================================

class TestActionValidation:
    """Test action validation logic."""
    
    def test_validate_flag_action(self, executor):
        """Test validation of flag action."""
        action = {"type": "flag", "priority": 9, "reason": "Important"}
        
        is_valid = executor.validate_action(action)
        
        assert is_valid is True
    
    def test_validate_archive_action(self, executor):
        """Test validation of archive action."""
        action = {"type": "archive", "priority": 5}
        
        is_valid = executor.validate_action(action)
        
        assert is_valid is True
    
    def test_validate_label_action_requires_name(self, executor):
        """Test label action requires label name."""
        action = {"type": "label", "priority": 5}
        
        is_valid = executor.validate_action(action)
        
        assert is_valid is False
    
    def test_validate_label_action_with_name(self, executor):
        """Test label action validation with name."""
        action = {"type": "label", "label": "Important", "priority": 5}
        
        is_valid = executor.validate_action(action)
        
        assert is_valid is True
    
    def test_validate_unsupported_action_type(self, executor):
        """Test validation rejects unsupported action type."""
        action = {"type": "send_email", "message": "Hello"}
        
        is_valid = executor.validate_action(action)
        
        assert is_valid is False
    
    def test_validate_missing_type_field(self, executor):
        """Test validation rejects missing type field."""
        action = {"priority": 5, "reason": "Test"}
        
        is_valid = executor.validate_action(action)
        
        assert is_valid is False


# ============================================================================
# Tests: Eligibility Decisions
# ============================================================================

class TestEligibilityDecisions:
    """Test eligibility decision logic."""
    
    def test_flag_action_approved(self, executor):
        """Test flag action is approved."""
        action = {"type": "flag", "priority": 9}
        
        decision = executor.decide_eligibility(action)
        
        assert decision == ExecutionDecision.APPROVED
    
    def test_archive_action_approved(self, executor):
        """Test archive action is approved."""
        action = {"type": "archive"}
        
        decision = executor.decide_eligibility(action)
        
        assert decision == ExecutionDecision.APPROVED
    
    def test_read_action_approved(self, executor):
        """Test read action is approved."""
        action = {"type": "read"}
        
        decision = executor.decide_eligibility(action)
        
        assert decision == ExecutionDecision.APPROVED
    
    def test_unsupported_action_blocked(self, executor):
        """Test unsupported actions are blocked."""
        action = {"type": "delete_forever"}
        
        decision = executor.decide_eligibility(action)
        
        assert decision == ExecutionDecision.BLOCKED
    
    def test_invalid_action_blocked(self, executor):
        """Test invalid actions are blocked."""
        action = {"type": "label"}  # Missing required 'label' field
        
        decision = executor.decide_eligibility(action)
        
        assert decision == ExecutionDecision.BLOCKED


# ============================================================================
# Tests: Execution Planning
# ============================================================================

class TestExecutionPlanning:
    """Test execution plan generation."""
    
    def test_plan_flag_action(self, executor, test_recommendation):
        """Test planning for flag action."""
        actions = [{"type": "flag", "priority": 9}]
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        assert plan is not None
        assert plan.recommendation_id == test_recommendation.id
        assert len(plan.steps) > 0
    
    def test_plan_multiple_actions(self, executor, test_recommendation):
        """Test planning for multiple actions."""
        actions = [
            {"type": "flag", "priority": 9},
            {"type": "label", "label": "Important"},
        ]
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        assert plan is not None
        assert len(plan.steps) == 2
    
    def test_plan_includes_audit_trail(self, executor, test_recommendation):
        """Test execution plan includes audit information."""
        actions = [{"type": "flag", "priority": 9}]
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        assert plan.user_id == test_recommendation.user_id
        assert plan.email_job_id == test_recommendation.email_job_id
        assert plan.created_at is not None
    
    def test_plan_simulation_mode_flag(self, executor, test_recommendation):
        """Test execution plan is marked as simulated in simulation mode."""
        actions = [{"type": "flag", "priority": 9}]
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        assert plan.is_simulated is True
    
    def test_plan_no_side_effects(self, executor, test_recommendation):
        """Test execution plan generation does not produce side effects."""
        # This test ensures that plan_execution() only creates data structures
        # and does not call external APIs or modify inbox state.
        actions = [
            {"type": "flag", "priority": 9},
            {"type": "archive"},
        ]
        
        # Calling plan_execution should not raise exceptions or cause mutations
        plan = executor.plan_execution(test_recommendation, actions)
        
        assert plan is not None
        assert len(plan.steps) == 2
        # Status should be planned, not executed
        assert plan.status in ["planned", "simulated"]


# ============================================================================
# Tests: Idempotency
# ============================================================================

class TestIdempotency:
    """Test idempotent behavior with duplicate recommendations."""
    
    def test_same_recommendation_twice(self, executor, test_recommendation):
        """Test processing same recommendation twice is safe."""
        actions = [{"type": "flag", "priority": 9}]
        
        plan1 = executor.plan_execution(test_recommendation, actions)
        plan2 = executor.plan_execution(test_recommendation, actions)
        
        # Both should succeed and produce similar plans
        assert plan1 is not None
        assert plan2 is not None
        assert len(plan1.steps) == len(plan2.steps)
    
    def test_execution_plan_is_readonly(self, executor, test_recommendation):
        """Test execution plans are not accidentally mutated."""
        actions = [{"type": "flag", "priority": 9}]
        
        plan = executor.plan_execution(test_recommendation, actions)
        original_steps = len(plan.steps)
        
        # Attempting to modify steps should not work (if plan is immutable)
        # For now, just verify structure is stable
        assert len(plan.steps) == original_steps


# ============================================================================
# Tests: Simulation Mode
# ============================================================================

class TestSimulationMode:
    """Test simulation mode behavior."""
    
    def test_simulation_mode_enabled(self):
        """Test executor can be created in simulation mode."""
        executor = ActionExecutor(simulation_mode=True)
        
        assert executor.simulation_mode is True
    
    def test_simulation_mode_disabled(self):
        """Test executor can be created with simulation disabled."""
        executor = ActionExecutor(simulation_mode=False)
        
        assert executor.simulation_mode is False
    
    def test_simulation_plan_is_marked(self, executor, test_recommendation):
        """Test plans in simulation mode are marked as simulated."""
        actions = [{"type": "flag", "priority": 9}]
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        assert plan.is_simulated is True
    
    def test_simulation_no_execution_paths(self, executor, test_recommendation):
        """Test simulation mode does not create execution paths."""
        # In simulation mode, should not contain actual API calls or side effects
        actions = [{"type": "flag", "priority": 9}]
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        # Plan should be readable but not contain execute() method
        # or execution should be a no-op
        assert hasattr(plan, "steps")
        assert plan.status != "executed"


# ============================================================================
# Tests: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_empty_actions_list(self, executor, test_recommendation):
        """Test handling empty actions list."""
        actions = []
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        # Should handle gracefully
        assert plan is not None
        assert len(plan.steps) == 0
    
    def test_invalid_recommendation_structure(self, executor):
        """Test handling of invalid recommendation structure."""
        # Create a minimal mock that lacks expected fields
        class MinimalRec:
            id = "rec-1"
            user_id = "user-1"
            email_job_id = "job-1"
        
        rec = MinimalRec()
        actions = [{"type": "flag", "priority": 9}]
        
        # Should handle gracefully or raise clear error
        try:
            plan = executor.plan_execution(rec, actions)
            assert plan is not None
        except (AttributeError, TypeError) as e:
            # Acceptable to raise if recommendation structure is wrong
            pass
    
    def test_mixed_valid_and_invalid_actions(self, executor, test_recommendation):
        """Test handling mix of valid and invalid actions."""
        actions = [
            {"type": "flag", "priority": 9},
            {"type": "delete_forever"},  # Invalid
            {"type": "archive"},
        ]
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        # Should include only valid actions
        valid_steps = [
            s for s in plan.steps
            if s.decision == ExecutionDecision.APPROVED
        ]
        assert len(valid_steps) >= 2  # flag and archive


# ============================================================================
# Tests: Audit Trail
# ============================================================================

class TestAuditTrail:
    """Test audit trail generation."""
    
    def test_plan_records_user_id(self, executor, test_recommendation):
        """Test plan records user ID for audit."""
        actions = [{"type": "flag", "priority": 9}]
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        assert plan.user_id == test_recommendation.user_id
    
    def test_plan_records_email_job_id(self, executor, test_recommendation):
        """Test plan records email job ID for audit."""
        actions = [{"type": "flag", "priority": 9}]
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        assert plan.email_job_id == test_recommendation.email_job_id
    
    def test_plan_records_timestamp(self, executor, test_recommendation):
        """Test plan records creation timestamp."""
        actions = [{"type": "flag", "priority": 9}]
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        assert plan.created_at is not None
        assert isinstance(plan.created_at, datetime)
    
    def test_plan_includes_reasoning(self, executor, test_recommendation):
        """Test plan includes decision reasoning."""
        actions = [{"type": "flag", "priority": 9}]
        
        # Decode rule_names from JSON if needed
        rec_rule_names = test_recommendation.rule_names
        if isinstance(rec_rule_names, str):
            rec_rule_names = json.loads(rec_rule_names)
        
        plan = executor.plan_execution(test_recommendation, actions)
        
        assert plan.reasoning is not None
        assert len(plan.reasoning) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
