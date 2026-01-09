"""
Gmail OAuth2 connector.
Handles Gmail authentication and email fetching.
"""
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import base64
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GmailConnector:
    """
    Gmail OAuth2 connector for email management.
    
    Handles:
    - OAuth2 authorization flow
    - Token refresh
    - Email fetching and parsing
    - Email operations (flag, archive, etc.)
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize Gmail connector.
        
        Args:
            client_id: Gmail OAuth2 client ID
            client_secret: Gmail OAuth2 client secret
            redirect_uri: OAuth2 redirect URI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = [
            "https://www.googleapis.com/auth/gmail.modify",
        ]
        # Build client_secrets config for google-auth-oauthlib
        self.client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }

    def get_authorization_url(self, state: str) -> str:
        """
        Generate Gmail OAuth2 authorization URL.
        
        Args:
            state: State parameter for CSRF protection
            
        Returns:
            Authorization URL for user to visit
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            state=state,
            redirect_uri=self.redirect_uri,
        )
        auth_url, _ = flow.authorization_url(prompt="consent")
        return auth_url

    def handle_oauth_callback(self, code: str, state: str = None) -> Dict[str, Any]:
        """
        Handle OAuth2 callback from Gmail.
        
        Args:
            code: Authorization code from OAuth2 flow
            state: State parameter (optional, for security)
            
        Returns:
            Dictionary with access_token, refresh_token, expires_in
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            state=state,
            redirect_uri=self.redirect_uri,
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Extract token info
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_in": int((credentials.expiry - datetime.utcnow()).total_seconds()),
            "expires_at": credentials.expiry.isoformat(),
        }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh expired access token.
        
        Args:
            refresh_token: Refresh token from previous auth
            
        Returns:
            New access token and expiration
        """
        from google.auth.transport.requests import Request
        
        # Create credentials from refresh token
        credentials = Credentials(
            token=None,  # No current access token
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        
        # Refresh the token
        request = Request()
        credentials.refresh(request)
        
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_in": int((credentials.expiry - datetime.utcnow()).total_seconds()),
            "expires_at": credentials.expiry.isoformat(),
        }


    def fetch_emails(
        self,
        access_token: str,
        max_results: int = 10,
        query: str = "is:unread",
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from Gmail inbox.
        
        Args:
            access_token: Valid Gmail access token
            max_results: Maximum number of emails to fetch
            query: Gmail search query (default: unread emails)
            
        Returns:
            List of email dictionaries with metadata
        """
        try:
            # Create Gmail service with access token
            service = build(
                "gmail",
                "v1",
                credentials=Credentials(token=access_token),
            )
            
            # List messages matching query
            results = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results,
                fields="messages(id,threadId)",
            ).execute()
            
            messages = results.get("messages", [])
            logger.info(f"Fetched {len(messages)} messages from Gmail")
            
            emails = []
            for message in messages:
                email_data = self._parse_message(service, message["id"])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails from Gmail: {e}")
            raise

    def _parse_message(self, service, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Parse full message content from Gmail API.
        
        Args:
            service: Gmail service instance
            message_id: Gmail message ID
            
        Returns:
            Dictionary with parsed email data
        """
        try:
            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",
            ).execute()
            
            headers = message["payload"]["headers"]
            headers_dict = {h["name"]: h["value"] for h in headers}
            
            # Extract body
            body = ""
            if "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        if "data" in part["body"]:
                            body = base64.urlsafe_b64decode(
                                part["body"]["data"]
                            ).decode("utf-8")
                            break
            else:
                if "data" in message["payload"]["body"]:
                    body = base64.urlsafe_b64decode(
                        message["payload"]["body"]["data"]
                    ).decode("utf-8")
            
            return {
                "message_id": message_id,
                "thread_id": message.get("threadId"),
                "subject": headers_dict.get("Subject", ""),
                "from": headers_dict.get("From", ""),
                "to": headers_dict.get("To", ""),
                "cc": headers_dict.get("Cc", ""),
                "date": headers_dict.get("Date", ""),
                "body": body,
                "labels": message.get("labelIds", []),
                "is_unread": "UNREAD" in message.get("labelIds", []),
            }
            
        except Exception as e:
            logger.error(f"Error parsing message {message_id}: {e}")
            return None

    def get_email_body(self, access_token: str, message_id: str) -> str:
        """
        Get full email body/content.
        
        Args:
            access_token: Valid Gmail access token
            message_id: Gmail message ID
            
        Returns:
            Email body text
        """
        try:
            service = build(
                "gmail",
                "v1",
                credentials=Credentials(token=access_token),
            )
            email = self._parse_message(service, message_id)
            return email["body"] if email else ""
        except Exception as e:
            logger.error(f"Error getting email body: {e}")
            return ""

    def send_email(
        self,
        access_token: str,
        to: str,
        subject: str,
        body: str,
        in_reply_to: Optional[str] = None,
    ) -> str:
        """
        Send an email via Gmail.
        
        Args:
            access_token: Valid Gmail access token
            to: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            in_reply_to: Optional message ID to reply to
            
        Returns:
            Sent message ID
        """
        # To be implemented in Phase B (not part of MVP)
        raise NotImplementedError("To be implemented in Phase B")

    def label_email(
        self,
        access_token: str,
        message_id: str,
        labels: list,
    ) -> bool:
        """
        Apply labels/tags to an email.
        
        Args:
            access_token: Valid Gmail access token
            message_id: Gmail message ID
            labels: List of label names
            
        Returns:
            Success status
        """
        # To be implemented in Phase B (not part of MVP)
        raise NotImplementedError("To be implemented in Phase B")

    def archive_email(self, access_token: str, message_id: str) -> bool:
        """
        Archive an email (remove from inbox).
        
        Args:
            access_token: Valid Gmail access token
            message_id: Gmail message ID
            
        Returns:
            Success status
        """
        # To be implemented in Phase B (not part of MVP)
        raise NotImplementedError("To be implemented in Phase B")

    def star_email(self, access_token: str, message_id: str) -> bool:
        """
        Star/flag an email.
        
        Args:
            access_token: Valid Gmail access token
            message_id: Gmail message ID
            
        Returns:
            Success status
        """
        # To be implemented in Phase B (not part of MVP)
        raise NotImplementedError("To be implemented in Phase B")

    def get_email_body(self, access_token: str, message_id: str) -> str:
        """
        Get full email body/content.
        
        Args:
            access_token: Valid Gmail access token
            message_id: Gmail message ID
            
        Returns:
            Email body text
        """
        # To be implemented in Phase B
        raise NotImplementedError("To be implemented in Phase B")

    def send_email(
        self,
        access_token: str,
        to: str,
        subject: str,
        body: str,
        in_reply_to: Optional[str] = None,
    ) -> str:
        """
        Send an email via Gmail.
        
        Args:
            access_token: Valid Gmail access token
            to: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            in_reply_to: Optional message ID to reply to
            
        Returns:
            Sent message ID
        """
        # To be implemented in Phase B
        raise NotImplementedError("To be implemented in Phase B")

    def label_email(
        self,
        access_token: str,
        message_id: str,
        labels: list,
    ) -> bool:
        """
        Apply labels/tags to an email.
        
        Args:
            access_token: Valid Gmail access token
            message_id: Gmail message ID
            labels: List of label names
            
        Returns:
            Success status
        """
        # To be implemented in Phase B
        raise NotImplementedError("To be implemented in Phase B")

    def archive_email(self, access_token: str, message_id: str) -> bool:
        """
        Archive an email (remove from inbox).
        
        Args:
            access_token: Valid Gmail access token
            message_id: Gmail message ID
            
        Returns:
            Success status
        """
        # To be implemented in Phase B
        raise NotImplementedError("To be implemented in Phase B")

    def star_email(self, access_token: str, message_id: str) -> bool:
        """
        Star/flag an email.
        
        Args:
            access_token: Valid Gmail access token
            message_id: Gmail message ID
            
        Returns:
            Success status
        """
        # To be implemented in Phase B
        raise NotImplementedError("To be implemented in Phase B")


class OutlookConnector:
    """
    Outlook OAuth2 connector (future implementation).
    
    Handles Outlook/Microsoft Graph API integration.
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """Initialize Outlook connector."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """To be implemented in Phase B."""
        raise NotImplementedError("To be implemented in Phase C")

    def handle_oauth_callback(self, code: str) -> Dict[str, Any]:
        """To be implemented in Phase B."""
        raise NotImplementedError("To be implemented in Phase C")

    def fetch_emails(self, access_token: str, max_results: int = 10) -> list:
        """To be implemented in Phase B."""
        raise NotImplementedError("To be implemented in Phase C")

    def send_email(self, access_token: str, to: str, subject: str, body: str) -> str:
        """To be implemented in Phase B."""
        raise NotImplementedError("To be implemented in Phase C")


# ============================================================================
# Connector Factory
# ============================================================================


class EmailConnectorFactory:
    """
    Factory for creating email connector instances.
    
    Supports multiple email providers with unified interface.
    """

    _connectors = {
        "gmail": GmailConnector,
        "outlook": OutlookConnector,
    }

    @classmethod
    def create(cls, provider: str, **kwargs) -> Any:
        """
        Create connector for specified provider.
        
        Args:
            provider: Email provider ('gmail', 'outlook', etc.)
            **kwargs: Provider-specific configuration
            
        Returns:
            Connector instance
            
        Raises:
            ValueError: If provider not supported
        """
        if provider not in cls._connectors:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported: {list(cls._connectors.keys())}"
            )

        connector_class = cls._connectors[provider]
        return connector_class(**kwargs)

    @classmethod
    def register(cls, provider: str, connector_class):
        """
        Register a new email connector.
        
        Args:
            provider: Provider name
            connector_class: Connector class
        """
        cls._connectors[provider] = connector_class

    @classmethod
    def get_supported_providers(cls) -> list:
        """Get list of supported email providers."""
        return list(cls._connectors.keys())
