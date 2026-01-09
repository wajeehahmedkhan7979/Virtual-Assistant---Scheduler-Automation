"""
Initialize connectors package.
"""
from .gmail import GmailConnector, OutlookConnector, EmailConnectorFactory

__all__ = [
    "GmailConnector",
    "OutlookConnector",
    "EmailConnectorFactory",
]
