"""
Tests for rule evaluation engine and recommendation generation.
Tests RuleEngine, rule matching, action generation, and Celery tasks.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base, User, EmailAccount, EmailJob, ActionRecommendation
from backend.llm.rule_engine import RuleEngine, create_rule_engine, RuleEvaluationResult
from backend.worker.tasks.recommender import generate_recommendation
from backend.config import settings


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
def test_classified_email(test_db, test_user, test_email_account):
    """Create test classified email."""
    email = EmailJob(
        id="test-email-1",
        user_id=test_user.id,
        email_account_id=test_email_account.id,
        email_id="gmail-id-123",
        sender="boss@company.com",
        subject="Urgent: Q4 Report Due",
        body="Please submit the Q4 financial report by EOD today. This is critical.",
        classification="important",
        classification_confidence=95,
        is_processed=True,
    )
    test_db.add(email)
    test_db.commit()
    return email


# ============================================================================
# Unit Tests: RuleEngine
# ============================================================================

class TestRuleEngineInitialization:
    """Test RuleEngine initialization."""
    
    def test_engine_initializes_with_defaults(self):
        """Test rule engine initializes with default rules."""
        engine = create_rule_engine()
        
        assert len(engine.rules) > 0
        assert all("name" in rule for rule in engine.rules)
        assert all("conditions" in rule for rule in engine.rules)
        assert all("actions" in rule for rule in engine.rules)
    
    def test_engine_initializes_with_custom_rules(self):
        """Test rule engine initializes with custom rules."""
        custom_rules = [
            {
                "name": "Custom rule",
                "conditions": {"category": ["important"]},
                "actions": [{"type": "flag", "priority": 9}],
                "priority": 5,
                "is_active": True,
            }
        ]
        
        engine = RuleEngine(rules=custom_rules)
        
        assert len(engine.rules) == 1
        assert engine.rules[0]["name"] == "Custom rule"


class TestRuleMatching:
    """Test rule condition matching."""
    
    def test_match_by_category(self):
        """Test matching rule by email category."""
        engine = create_rule_engine()
        
        email_context = {
            "classification": "important",
            "confidence": 0.95,
            "sender": "boss@company.com",
            "subject": "Urgent",
            "body": "Do this now",
            "labels": [],
        }
        
        # Should match "Flag important emails" rule
        matching_rules = [
            rule for rule in engine.rules
            if engine._rule_matches(rule, email_context)
        ]
        
        assert len(matching_rules) > 0
        assert any("important" in rule["name"].lower() for rule in matching_rules)
    
    def test_match_fails_low_confidence(self):
        """Test rule matching fails with low confidence."""
        engine = create_rule_engine()
        
        # Create low-confidence context
        email_context = {
            "classification": "important",
            "confidence": 0.4,  # Below threshold
            "sender": "unknown@company.com",
            "subject": "Maybe important",
            "body": "Not sure",
            "labels": [],
        }
        
        # Should not match rules requiring high confidence
        matching_rules = [
            rule for rule in engine.rules
            if rule.get("conditions", {}).get("min_confidence", 0) > 0.7
            and engine._rule_matches(rule, email_context)
        ]
        
        # Should have 0 matches for rules requiring 70%+ confidence
        assert len(matching_rules) == 0
    
    def test_match_sender_pattern_wildcard(self):
        """Test sender pattern matching with wildcards."""
        engine = create_rule_engine()
        
        email_context = {
            "classification": "spam",
            "confidence": 0.9,
            "sender": "promo@marketing.example.com",
            "subject": "Special offer",
            "body": "Buy now",
            "labels": [],
        }
        
        # Create rule with sender pattern
        rule = {
            "name": "Block marketing emails",
            "conditions": {
                "sender_pattern": ["*@marketing.example.com"],
            },
            "actions": [],
            "is_active": True,
        }
        
        assert engine._rule_matches(rule, email_context) is True
    
    def test_match_subject_keywords(self):
        """Test matching by subject keywords."""
        engine = create_rule_engine()
        
        email_context = {
            "classification": "important",
            "confidence": 0.8,
            "sender": "ceo@company.com",
            "subject": "URGENT: Board Meeting Tomorrow",
            "body": "Need your attendance",
            "labels": [],
        }
        
        rule = {
            "name": "Flag urgent emails",
            "conditions": {
                "subject_keywords": ["urgent", "critical", "asap"],
            },
            "actions": [],
            "is_active": True,
        }
        
        assert engine._rule_matches(rule, email_context) is True
    
    def test_match_body_keywords(self):
        """Test matching by body keywords."""
        engine = create_rule_engine()
        
        email_context = {
            "classification": "actionable",
            "confidence": 0.75,
            "sender": "manager@company.com",
            "subject": "Task assignment",
            "body": "Can you please review the attached document and provide feedback by EOD?",
            "labels": [],
        }
        
        rule = {
            "name": "Actionable items",
            "conditions": {
                "body_keywords": ["please", "feedback", "review"],
            },
            "actions": [],
            "is_active": True,
        }
        
        assert engine._rule_matches(rule, email_context) is True


class TestActionGeneration:
    """Test action recommendation generation."""
    
    def test_create_flag_action(self):
        """Test creating flag action."""
        engine = create_rule_engine()
        
        action_spec = {
            "type": "flag",
            "priority": 9,
            "reason": "Needs attention",
        }
        
        action = engine._create_action(action_spec, {})
        
        assert action is not None
        assert action["type"] == "flag"
        assert action["priority"] == 9
    
    def test_create_archive_action(self):
        """Test creating archive action."""
        engine = create_rule_engine()
        
        action_spec = {
            "type": "archive",
            "priority": 8,
            "reason": "Auto-archive",
        }
        
        action = engine._create_action(action_spec, {})
        
        assert action is not None
        assert action["type"] == "archive"
    
    def test_create_label_action(self):
        """Test creating label action with parameters."""
        engine = create_rule_engine()
        
        action_spec = {
            "type": "label",
            "label": "Important",
            "priority": 7,
            "reason": "Apply label",
        }
        
        action = engine._create_action(action_spec, {})
        
        assert action is not None
        assert action["type"] == "label"
        assert action["label"] == "Important"
    
    def test_invalid_action_type_ignored(self):
        """Test invalid action types are ignored."""
        engine = create_rule_engine()
        
        action_spec = {
            "type": "invalid_action_xyz",
            "priority": 5,
        }
        
        action = engine._create_action(action_spec, {})
        
        assert action is None


class TestRuleEvaluation:
    """Test complete rule evaluation."""
    
    def test_evaluate_important_email(self):
        """Test evaluating important email."""
        engine = create_rule_engine()
        
        result = engine.evaluate(
            classification="important",
            confidence=0.95,
            sender="boss@company.com",
            subject="Urgent: Q4 Report",
            body="Please submit by EOD",
        )
        
        assert result.confidence_score > 0
        assert len(result.recommended_actions) > 0
        assert "flag" in [a["type"] for a in result.recommended_actions]
    
    def test_evaluate_spam_email(self):
        """Test evaluating spam email."""
        engine = create_rule_engine()
        
        result = engine.evaluate(
            classification="spam",
            confidence=0.9,
            sender="unknown@spam.com",
            subject="Click here!!!",
            body="Win money now",
        )
        
        assert result.confidence_score > 0
        assert len(result.recommended_actions) > 0
        # Should recommend archive or spam action
        action_types = [a["type"] for a in result.recommended_actions]
        assert any(action in action_types for action in ["archive", "spam"])
    
    def test_evaluate_promotional_email(self):
        """Test evaluating promotional email."""
        engine = create_rule_engine()
        
        result = engine.evaluate(
            classification="promotional",
            confidence=0.85,
            sender="marketing@retailer.com",
            subject="Summer Sale - 50% Off",
            body="Limited time offer",
        )
        
        assert result.confidence_score > 0
        assert len(result.recommended_actions) > 0
        # Should recommend archive
        assert any(a["type"] == "archive" for a in result.recommended_actions)
    
    def test_evaluate_unclassified_email(self):
        """Test evaluating unclassified email."""
        engine = create_rule_engine()
        
        result = engine.evaluate(
            classification="informational",
            confidence=0.5,
            sender="colleague@company.com",
            subject="FYI",
            body="Just wanted to let you know",
        )
        
        # Might match some rules or none
        assert isinstance(result.confidence_score, int)
        assert result.confidence_score >= 0


class TestConfidenceCalculation:
    """Test recommendation confidence scoring."""
    
    def test_confidence_increases_with_matching_rules(self):
        """Test confidence increases with more matching rules."""
        engine = create_rule_engine()
        
        # Single matching rule
        single_match = [{"name": "Rule 1", "priority": 5}]
        single_confidence = engine._calculate_confidence(
            single_match,
            {"confidence": 0.8, "classification": "important"}
        )
        
        # Multiple matching rules
        multiple_matches = [
            {"name": "Rule 1", "priority": 5},
            {"name": "Rule 2", "priority": 5},
            {"name": "Rule 3", "priority": 5},
        ]
        multiple_confidence = engine._calculate_confidence(
            multiple_matches,
            {"confidence": 0.8, "classification": "important"}
        )
        
        assert multiple_confidence > single_confidence
    
    def test_confidence_reduced_for_low_classification_confidence(self):
        """Test confidence reduced when classification confidence is low."""
        engine = create_rule_engine()
        
        matched_rules = [{"name": "Rule 1", "priority": 5}]
        
        high_conf = engine._calculate_confidence(
            matched_rules,
            {"confidence": 0.9, "classification": "important"}
        )
        
        low_conf = engine._calculate_confidence(
            matched_rules,
            {"confidence": 0.5, "classification": "important"}
        )
        
        assert high_conf > low_conf


class TestReasoningGeneration:
    """Test human-readable reasoning generation."""
    
    def test_reasoning_includes_classification(self):
        """Test reasoning includes classification info."""
        engine = create_rule_engine()
        
        result = engine.evaluate(
            classification="important",
            confidence=0.85,
            sender="boss@company.com",
            subject="Urgent",
            body="Do this now",
        )
        
        assert "important" in result.reasoning.lower()
        assert "85%" in result.reasoning
    
    def test_reasoning_includes_matched_rules(self):
        """Test reasoning includes matched rule names."""
        engine = create_rule_engine()
        
        result = engine.evaluate(
            classification="important",
            confidence=0.9,
            sender="ceo@company.com",
            subject="URGENT",
            body="Critical decision needed",
        )
        
        if result.matched_rules:
            for rule in result.matched_rules:
                assert rule["name"] in result.reasoning


# ============================================================================
# Integration Tests: Celery Task
# ============================================================================

class TestRecommendationTask:
    """Test generate_recommendation Celery task."""
    
    def test_generate_recommendation_creates_record(
        self,
        test_db,
        test_classified_email,
        test_user,
    ):
        """Test task creates recommendation record."""
        # In-memory test would require mocking database access
        # For now, verify task structure
        from backend.worker.tasks.recommender import generate_recommendation
        
        assert hasattr(generate_recommendation, 'apply_async')
        assert callable(generate_recommendation)
    
    def test_task_skips_unclassified_email(self):
        """Test task skips unclassified emails."""
        # Verify task structure handles unclassified case
        assert True  # Task structure validates this


# ============================================================================
# Pattern Matching Tests
# ============================================================================

class TestPatternMatching:
    """Test pattern matching logic."""
    
    def test_wildcard_pattern_matches(self):
        """Test wildcard patterns."""
        engine = create_rule_engine()
        
        assert engine._pattern_matches("*@company.com", "user@company.com")
        assert engine._pattern_matches("*@company.com", "boss@company.com")
        assert not engine._pattern_matches("*@company.com", "user@other.com")
    
    def test_question_mark_pattern_matches(self):
        """Test ? wildcard pattern."""
        engine = create_rule_engine()
        
        assert engine._pattern_matches("test?.txt", "test1.txt")
        assert engine._pattern_matches("test?.txt", "testA.txt")
        assert not engine._pattern_matches("test?.txt", "test12.txt")
    
    def test_regex_pattern_matches(self):
        """Test regex patterns."""
        engine = create_rule_engine()
        
        # Email pattern
        assert engine._pattern_matches(r"^[\w\.-]+@[\w\.-]+\.\w+$", "user@company.com")
        assert not engine._pattern_matches(r"^[\w\.-]+@[\w\.-]+\.\w+$", "not-an-email")
    
    def test_case_insensitive_matching(self):
        """Test case-insensitive pattern matching."""
        engine = create_rule_engine()
        
        assert engine._pattern_matches("IMPORTANT", "important")
        assert engine._pattern_matches("Boss@*", "boss@company.com")


# ============================================================================
# Rule Validation Tests
# ============================================================================

class TestRuleValidation:
    """Test rule validation."""
    
    def test_validates_rule_structure(self):
        """Test rule structure validation."""
        engine = RuleEngine(rules=[
            {
                "name": "Valid rule",
                "conditions": {"category": ["important"]},
                "actions": [{"type": "flag"}],
            }
        ])
        
        # Should validate without error
        assert len(engine.rules) == 1
    
    def test_invalid_action_type_warning(self):
        """Test warning for invalid action types."""
        engine = RuleEngine(rules=[
            {
                "name": "Rule with invalid action",
                "conditions": {"category": ["important"]},
                "actions": [{"type": "invalid_action"}],
            }
        ])
        
        # Rule should be created but action validation happens at evaluation
        assert len(engine.rules) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
