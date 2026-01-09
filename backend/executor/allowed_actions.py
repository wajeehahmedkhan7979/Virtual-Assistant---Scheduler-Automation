"""
Allowed action types and validation schemas.
Defines which actions can be executed and their required fields.
"""

# List of allowed action types
# Each action must be approved by decide_eligibility() before execution planning
ALLOWED_ACTIONS = [
    "flag",      # Flag email for follow-up
    "archive",   # Archive email
    "label",     # Apply label
    "read",      # Mark as read
    "spam",      # Report as spam
]

# Action validation requirements
ACTION_REQUIRED_FIELDS = {
    "flag": ["type"],
    "archive": ["type"],
    "label": ["type", "label"],  # label field required
    "read": ["type"],
    "spam": ["type"],
}

# Action optional fields
ACTION_OPTIONAL_FIELDS = {
    "flag": ["priority", "reason"],
    "archive": ["priority"],
    "label": ["priority"],
    "read": ["priority"],
    "spam": ["priority"],
}


def is_action_type_allowed(action_type: str) -> bool:
    """
    Check if action type is in allowed list.
    
    Args:
        action_type: The action type to check
    
    Returns:
        True if action type is allowed, False otherwise
    """
    return action_type in ALLOWED_ACTIONS


def get_required_fields(action_type: str) -> list:
    """
    Get required fields for an action type.
    
    Args:
        action_type: The action type
    
    Returns:
        List of required field names
    """
    return ACTION_REQUIRED_FIELDS.get(action_type, ["type"])


def get_optional_fields(action_type: str) -> list:
    """
    Get optional fields for an action type.
    
    Args:
        action_type: The action type
    
    Returns:
        List of optional field names
    """
    return ACTION_OPTIONAL_FIELDS.get(action_type, [])
