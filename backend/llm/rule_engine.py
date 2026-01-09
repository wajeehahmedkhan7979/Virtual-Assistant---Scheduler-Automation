"""
Rule evaluation engine for generating action recommendations.
Evaluates email classification and metadata against user-defined rules.
Does NOT execute any actions - only generates recommendations.
"""
import logging
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class RuleEvaluationResult:
    """Result of evaluating rules against an email."""
    
    def __init__(self):
        self.matched_rules: List[Dict[str, Any]] = []
        self.recommended_actions: List[Dict[str, Any]] = []
        self.safety_flags: List[str] = []
        self.confidence_score: int = 0
        self.reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "matched_rules": self.matched_rules,
            "recommended_actions": self.recommended_actions,
            "safety_flags": self.safety_flags,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
        }


class RuleEngine:
    """
    Evaluate rules and generate action recommendations for emails.
    
    Rules are defined as JSON/dict with:
    - name: Rule identifier
    - description: Human-readable description
    - conditions: What triggers the rule
    - actions: What actions to recommend
    - priority: Importance of rule (1-10)
    """
    
    # Built-in action types (recommendations only, no execution)
    VALID_ACTIONS = {
        "archive": "Move email to archive",
        "label": "Apply label/tag to email",
        "flag": "Flag email for follow-up",
        "snooze": "Snooze email for later",
        "read": "Mark as read",
        "spam": "Report as spam",
        "reply_draft": "Draft a reply",
        "notify": "Send notification to user",
        "priority": "Set priority level",
        "delegate": "Suggest delegation",
    }
    
    def __init__(self, rules: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize rule engine.
        
        Args:
            rules: List of rule definitions
        """
        self.rules = rules or self._get_default_rules()
        self._validate_rules()
        logger.info(f"RuleEngine initialized with {len(self.rules)} rules")
    
    def evaluate(
        self,
        classification: str,
        confidence: float,
        sender: str,
        subject: str,
        body: str,
        labels: Optional[List[str]] = None,
    ) -> RuleEvaluationResult:
        """
        Evaluate all rules against email metadata.
        
        Args:
            classification: Email classification category
            confidence: Classification confidence (0-1)
            sender: Email sender address
            subject: Email subject
            body: Email body (truncated OK)
            labels: Gmail labels (optional)
            
        Returns:
            RuleEvaluationResult with recommendations and reasoning
        """
        result = RuleEvaluationResult()
        
        # Build email context for rule evaluation
        email_context = {
            "classification": classification,
            "confidence": confidence,
            "sender": sender,
            "subject": subject,
            "body": body,
            "labels": labels or [],
        }
        
        # Evaluate each rule
        for rule in self.rules:
            if not rule.get("is_active", True):
                continue
            
            if self._rule_matches(rule, email_context):
                result.matched_rules.append({
                    "name": rule["name"],
                    "priority": rule.get("priority", 5),
                })
                
                # Generate actions from rule
                actions = rule.get("actions", [])
                for action in actions:
                    action_obj = self._create_action(action, email_context)
                    if action_obj:
                        result.recommended_actions.append(action_obj)
                
                # Check for safety flags
                flags = rule.get("safety_flags", [])
                result.safety_flags.extend(flags)
        
        # Sort actions by priority
        result.recommended_actions.sort(
            key=lambda x: x.get("priority", 5),
            reverse=True
        )
        
        # Generate reasoning and confidence
        if result.matched_rules:
            result.confidence_score = self._calculate_confidence(
                result.matched_rules,
                email_context
            )
            result.reasoning = self._generate_reasoning(
                result.matched_rules,
                result.recommended_actions,
                email_context
            )
        
        return result
    
    def _rule_matches(
        self,
        rule: Dict[str, Any],
        email_context: Dict[str, Any]
    ) -> bool:
        """
        Check if a rule matches the email context.
        
        Args:
            rule: Rule definition
            email_context: Email metadata
            
        Returns:
            True if all conditions match
        """
        conditions = rule.get("conditions", {})
        
        # Check category condition
        categories = conditions.get("category", [])
        if categories and email_context["classification"] not in categories:
            return False
        
        # Check confidence threshold
        min_confidence = conditions.get("min_confidence", 0)
        if email_context["confidence"] < min_confidence:
            return False
        
        # Check sender pattern
        sender_patterns = conditions.get("sender_pattern", [])
        if sender_patterns:
            sender_match = any(
                self._pattern_matches(pattern, email_context["sender"])
                for pattern in sender_patterns
            )
            if not sender_match:
                return False
        
        # Check subject keywords
        subject_keywords = conditions.get("subject_keywords", [])
        if subject_keywords:
            subject_match = any(
                keyword.lower() in email_context["subject"].lower()
                for keyword in subject_keywords
            )
            if not subject_match:
                return False
        
        # Check body keywords
        body_keywords = conditions.get("body_keywords", [])
        if body_keywords:
            body_match = any(
                keyword.lower() in email_context["body"].lower()
                for keyword in body_keywords
            )
            if not body_match:
                return False
        
        # Check labels (if present)
        required_labels = conditions.get("labels", [])
        if required_labels:
            label_match = any(
                label in email_context["labels"]
                for label in required_labels
            )
            if not label_match:
                return False
        
        return True
    
    def _pattern_matches(self, pattern: str, text: str) -> bool:
        """
        Check if pattern matches text.
        Supports wildcards (* and ?) and regex.
        
        Args:
            pattern: Pattern with * or ? wildcards
            text: Text to match
            
        Returns:
            True if matches
        """
        try:
            # Try regex first (if pattern looks like regex)
            if pattern.startswith("^") or pattern.startswith("("):
                return bool(re.search(pattern, text))
            
            # Convert wildcard pattern to regex
            regex_pattern = pattern.replace(".", r"\.")
            regex_pattern = regex_pattern.replace("*", ".*")
            regex_pattern = regex_pattern.replace("?", ".")
            
            return bool(re.match(regex_pattern, text, re.IGNORECASE))
        except Exception as e:
            logger.warning(f"Pattern match error: {e}")
            return False
    
    def _create_action(
        self,
        action_spec: Dict[str, Any],
        email_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create an action recommendation.
        
        Args:
            action_spec: Action specification from rule
            email_context: Email metadata
            
        Returns:
            Action object with details, or None if invalid
        """
        action_type = action_spec.get("type")
        
        # Validate action type
        if action_type not in self.VALID_ACTIONS:
            logger.warning(f"Unknown action type: {action_type}")
            return None
        
        action = {
            "type": action_type,
            "description": self.VALID_ACTIONS[action_type],
            "priority": action_spec.get("priority", 5),
            "reason": action_spec.get("reason", ""),
        }
        
        # Add action-specific parameters
        if action_type == "label":
            action["label"] = action_spec.get("label", "")
        elif action_type == "snooze":
            action["hours"] = action_spec.get("hours", 24)
        elif action_type == "reply_draft":
            action["template"] = action_spec.get("template", "")
        elif action_type == "priority":
            action["level"] = action_spec.get("level", "normal")  # low, normal, high, urgent
        elif action_type == "delegate":
            action["recipient"] = action_spec.get("recipient", "")
        
        return action
    
    def _calculate_confidence(
        self,
        matched_rules: List[Dict[str, str]],
        email_context: Dict[str, Any]
    ) -> int:
        """
        Calculate recommendation confidence (0-100).
        
        Args:
            matched_rules: List of matched rules
            email_context: Email metadata
            
        Returns:
            Confidence score 0-100
        """
        if not matched_rules:
            return 0
        
        # Base score from classification confidence
        base_score = int(email_context["confidence"] * 100)
        
        # Boost for multiple matching rules
        rule_boost = min(len(matched_rules) * 10, 30)
        
        # Reduce if confidence is low
        if email_context["confidence"] < 0.6:
            base_score = max(base_score - 20, 0)
        
        confidence = min(base_score + rule_boost, 100)
        return max(confidence, 0)
    
    def _generate_reasoning(
        self,
        matched_rules: List[Dict[str, str]],
        actions: List[Dict[str, Any]],
        email_context: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable explanation.
        
        Args:
            matched_rules: Matched rules
            actions: Recommended actions
            email_context: Email metadata
            
        Returns:
            Plain text explanation
        """
        parts = []
        
        # Email classification
        parts.append(
            f"Email classified as '{email_context['classification']}' "
            f"with {email_context['confidence']:.0%} confidence."
        )
        
        # Matched rules
        if matched_rules:
            rule_names = ", ".join(r["name"] for r in matched_rules)
            parts.append(f"Matched rules: {rule_names}.")
        
        # Recommended actions
        if actions:
            action_types = ", ".join(a["type"] for a in actions)
            parts.append(f"Recommending actions: {action_types}.")
        
        return " ".join(parts)
    
    def _validate_rules(self):
        """Validate rule definitions."""
        for rule in self.rules:
            # Validate structure
            if "name" not in rule:
                logger.warning("Rule missing 'name'")
                continue
            
            if "conditions" not in rule:
                logger.warning(f"Rule '{rule['name']}' missing 'conditions'")
                continue
            
            if "actions" not in rule:
                logger.warning(f"Rule '{rule['name']}' missing 'actions'")
                continue
            
            # Validate action types
            for action in rule.get("actions", []):
                if action.get("type") not in self.VALID_ACTIONS:
                    logger.warning(
                        f"Rule '{rule['name']}' has invalid action type: {action.get('type')}"
                    )
    
    def _get_default_rules(self) -> List[Dict[str, Any]]:
        """
        Return default rule set.
        Can be overridden by user rules.
        """
        return [
            {
                "name": "Flag important emails",
                "description": "Flag emails classified as important",
                "conditions": {
                    "category": ["important"],
                    "min_confidence": 0.7,
                },
                "actions": [
                    {
                        "type": "flag",
                        "priority": 9,
                        "reason": "High-priority email flagged for immediate attention",
                    }
                ],
                "priority": 9,
                "is_active": True,
            },
            {
                "name": "Archive promotional emails",
                "description": "Automatically archive promotional content",
                "conditions": {
                    "category": ["promotional"],
                    "min_confidence": 0.8,
                },
                "actions": [
                    {
                        "type": "archive",
                        "priority": 8,
                        "reason": "Promotional content archived",
                    },
                    {
                        "type": "label",
                        "label": "Promotions",
                        "priority": 7,
                        "reason": "Tagged for organization",
                    },
                ],
                "priority": 5,
                "is_active": True,
            },
            {
                "name": "Mark spam as read",
                "description": "Mark detected spam as read to declutter inbox",
                "conditions": {
                    "category": ["spam"],
                    "min_confidence": 0.85,
                },
                "actions": [
                    {
                        "type": "read",
                        "priority": 9,
                        "reason": "Spam marked as read to reduce visual clutter",
                    },
                    {
                        "type": "spam",
                        "priority": 8,
                        "reason": "Report to spam service",
                    },
                ],
                "priority": 7,
                "is_active": True,
            },
            {
                "name": "Flag follow-up emails",
                "description": "Flag emails needing follow-up",
                "conditions": {
                    "category": ["followup"],
                    "min_confidence": 0.6,
                },
                "actions": [
                    {
                        "type": "flag",
                        "priority": 9,
                        "reason": "Follow-up needed",
                    },
                    {
                        "type": "snooze",
                        "hours": 24,
                        "priority": 8,
                        "reason": "Snooze for tomorrow",
                    },
                ],
                "priority": 8,
                "is_active": True,
            },
            {
                "name": "Draft replies for actionable emails",
                "description": "Suggest reply for actionable items",
                "conditions": {
                    "category": ["actionable"],
                    "min_confidence": 0.75,
                },
                "actions": [
                    {
                        "type": "reply_draft",
                        "template": "Thank you for your email. I will review and respond shortly.",
                        "priority": 7,
                        "reason": "Standard acknowledgment template",
                    },
                ],
                "priority": 6,
                "is_active": True,
            },
        ]


def create_rule_engine(user_rules: Optional[List[Dict[str, Any]]] = None) -> RuleEngine:
    """
    Factory function to create a configured RuleEngine.
    
    Args:
        user_rules: Optional user-defined rules to override defaults
        
    Returns:
        Configured RuleEngine instance
    """
    if user_rules:
        logger.info(f"Creating RuleEngine with {len(user_rules)} user rules")
        return RuleEngine(rules=user_rules)
    else:
        logger.info("Creating RuleEngine with default rules")
        return RuleEngine()
