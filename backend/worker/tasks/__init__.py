"""
Initialize worker tasks package.
"""
from .email_processor import (
    fetch_and_process_emails,
    classify_email,
    send_auto_reply,
    flag_email,
    analyze_data_file,
    scheduled_email_sync,
)

__all__ = [
    "fetch_and_process_emails",
    "classify_email",
    "send_auto_reply",
    "flag_email",
    "analyze_data_file",
    "scheduled_email_sync",
]
