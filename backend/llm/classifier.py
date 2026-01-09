"""
Email classification using LangChain + OpenAI.
Classifies emails into user-configurable categories.
"""
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from langchain_openai import ChatOpenAI
from backend.config import settings

logger = logging.getLogger(__name__)


class EmailClassifier:
    """
    Classify emails using LangChain + OpenAI.
    
    Categorizes emails based on configurable categories and returns:
    - category: Primary email category
    - confidence: Classification confidence (0-1)
    - explanation: Short explanation of classification
    """

    def __init__(self, model: str = None, temperature: float = None):
        """
        Initialize email classifier.
        
        Args:
            model: OpenAI model to use (default from config)
            temperature: Model temperature (default from config)
        """
        self.model = model or settings.openai_model
        self.temperature = temperature if temperature is not None else settings.openai_temperature
        self.confidence_threshold = settings.classification_confidence_threshold
        
        # Load categories from config
        try:
            self.categories = json.loads(settings.email_categories)
            logger.info(f"Loaded {len(self.categories)} email categories")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse email_categories config: {e}")
            self.categories = {
                "important": "Time-sensitive or high-priority emails",
                "actionable": "Contains tasks or action items",
                "followup": "Requires a follow-up response",
                "informational": "For reference only",
                "spam": "Unsolicited or unwanted messages",
                "promotional": "Marketing or promotional content",
            }
        
        # Initialize LangChain chat model
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set. Classification will fail.")
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                model_name=self.model,
                temperature=self.temperature,
                api_key=settings.openai_api_key,
            )

    def classify(
        self,
        sender: str,
        subject: str,
        body: str,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Classify an email.
        
        Args:
            sender: Email sender address
            subject: Email subject line
            body: Email body text (truncated to 2000 chars)
            user_context: Optional dict with user preferences
            
        Returns:
            Dictionary with:
            - category: Primary category (str, one of self.categories.keys())
            - confidence: Confidence score (float, 0-1)
            - explanation: Short explanation (str, plain text)
        """
        if not self.llm:
            raise ValueError("OpenAI API key not configured")
        
        # Truncate body to prevent token overload
        body_truncated = body[:2000] if body else ""
        
        # Build category descriptions for prompt
        category_list = "\n".join(
            [f"- {cat}: {desc}" for cat, desc in self.categories.items()]
        )
        
        # Create prompt
        prompt_text = f"""You are an email classification assistant. Classify the following email into ONE of these categories:

{category_list}

Email Details:
From: {sender}
Subject: {subject}
Body: {body_truncated}

Respond with a JSON object containing:
- "category": The category name (must be one of the listed categories)
- "confidence": A confidence score from 0.0 to 1.0
- "explanation": A brief (one sentence) explanation of why you chose this category

IMPORTANT: Respond ONLY with valid JSON, no other text."""
        
        try:
            # Call LLM
            response = self.llm.predict(prompt_text)
            
            # Parse response
            classification = self._parse_classification_response(response)
            logger.debug(f"Classified email from {sender}: {classification['category']} (confidence: {classification['confidence']})")
            
            return classification
            
        except Exception as e:
            logger.error(f"Classification error for email from {sender}: {e}")
            # Return safe default
            return {
                "category": "informational",
                "confidence": 0.5,
                "explanation": "Classification failed, defaulting to informational",
            }

    def _parse_classification_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response JSON.
        
        Args:
            response: LLM response (should be JSON)
            
        Returns:
            Dictionary with category, confidence, explanation
        """
        try:
            # Try to extract JSON from response
            data = json.loads(response)
            
            # Validate fields
            category = data.get("category", "informational")
            confidence = float(data.get("confidence", 0.5))
            explanation = str(data.get("explanation", ""))
            
            # Validate category is known
            if category not in self.categories:
                logger.warning(f"Unknown category from LLM: {category}, using informational")
                category = "informational"
            
            # Clamp confidence to 0-1
            confidence = max(0.0, min(1.0, confidence))
            
            return {
                "category": category,
                "confidence": confidence,
                "explanation": explanation[:200],  # Limit explanation length
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification response as JSON: {e}")
            logger.debug(f"Response was: {response}")
            raise ValueError("Invalid classification response format")

    def batch_classify(
        self,
        emails: list[Dict[str, str]],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> list[Dict[str, Any]]:
        """
        Classify multiple emails.
        
        Args:
            emails: List of dicts with sender, subject, body
            user_context: Optional user context
            
        Returns:
            List of classification results
        """
        results = []
        for email in emails:
            try:
                result = self.classify(
                    sender=email.get("sender", ""),
                    subject=email.get("subject", ""),
                    body=email.get("body", ""),
                    user_context=user_context,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to classify email: {e}")
                results.append({
                    "category": "informational",
                    "confidence": 0.0,
                    "explanation": "Classification failed",
                })
        
        return results

    def extract_action_items(self, body: str) -> list:
        """
        Extract action items from email body.
        
        Args:
            body: Email body text
            
        Returns:
            List of action item strings
        """
        # To be implemented in Phase C (not part of MVP)
        logger.info("extract_action_items not yet implemented")
        return []

    def suggest_reply(
        self,
        sender: str,
        subject: str,
        body: str,
    ) -> Optional[str]:
        """
        Generate suggested reply to email.
        
        Args:
            sender: Email sender
            subject: Email subject
            body: Email body
            
        Returns:
            Suggested reply text, or None
        """
        # To be implemented in Phase C (not part of MVP)
        logger.info("suggest_reply not yet implemented")
        return None
