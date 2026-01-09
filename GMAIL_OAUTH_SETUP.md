# Gmail OAuth2 Setup Guide

This guide explains how to set up Gmail OAuth2 credentials for the Virtual Assistant & Scheduler project.

## Overview

The application uses Gmail OAuth2 to securely authenticate users' Gmail accounts. The flow:

1. User clicks "Connect Gmail" in the application
2. Application redirects to Google OAuth consent screen
3. User grants permission to access their emails
4. Google redirects back to our callback endpoint with authorization code
5. Application exchanges code for access/refresh tokens
6. Tokens are encrypted and stored securely in the database
7. Application can now fetch and process emails on behalf of user

## Prerequisites

- Google Cloud Project
- Google Cloud Console access
- A domain/server where your app is hosted (or localhost for development)

## Step 1: Create a Google Cloud Project

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top
3. Click "NEW PROJECT"
4. Enter project name: "Virtual Assistant & Scheduler"
5. Click "CREATE"
6. Wait for project to be created, then select it

## Step 2: Enable Gmail API

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Gmail API"
3. Click on "Gmail API"
4. Click "ENABLE"

## Step 3: Create OAuth2 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click "CREATE CREDENTIALS" button
3. Select **OAuth client ID**
4. If prompted to create a consent screen first:

   - Click "CREATE CONSENT SCREEN"
   - Select **External** for User Type
   - Fill in required fields:
     - **App name**: Virtual Assistant & Scheduler
     - **User support email**: your-email@example.com
     - **Developer contact**: your-email@example.com
   - Click "SAVE AND CONTINUE"
   - Skip optional scopes, click "SAVE AND CONTINUE"
   - Click "BACK TO DASHBOARD"

5. Click "CREATE CREDENTIALS" > **OAuth client ID** again
6. Application type: Select **Web application**
7. Name: "Virtual Assistant Backend"
8. **Authorized redirect URIs**: Add these:

   - For development: `http://localhost:8000/api/v1/auth/gmail/callback`
   - For production: `https://yourdomain.com/api/v1/auth/gmail/callback`
   - For testing: `http://localhost:3000/auth/gmail/callback` (frontend)

9. Click "CREATE"
10. Copy the **Client ID** and **Client Secret** from the popup

## Step 4: Configure Application

1. Open `.env` file in project root (or create from `.env.example`)
2. Set these variables:

```bash
# Gmail OAuth2
GMAIL_CLIENT_ID=<your-client-id-from-step-3>.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=<your-client-secret-from-step-3>
GMAIL_REDIRECT_URI=http://localhost:8000/api/v1/auth/gmail/callback

# Encryption key for storing tokens (generate using Python)
ENCRYPTION_KEY=<your-fernet-key>
```

### Generate Encryption Key

Run this in Python to generate a Fernet encryption key:

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())
```

Copy the output and paste into `ENCRYPTION_KEY` in `.env`

## Step 5: Test the OAuth Flow

### Using API directly:

1. Start the application:

```bash
cd backend
python -m uvicorn main:app --reload
```

2. Register a test user:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "username": "testuser",
    "password": "TestPassword123",
    "full_name": "Test User"
  }'
```

3. Login to get JWT token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPassword123"
  }'
```

4. Copy the `access_token` from response

5. Start Gmail OAuth flow:

```bash
curl -X POST http://localhost:8000/api/v1/auth/gmail/authorize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-access-token>" \
  -d '{}'
```

6. Copy the `authorization_url` from response
7. Visit the URL in your browser
8. Grant permission to the application
9. Google will redirect to callback endpoint
10. Response will contain `access_token` and `refresh_token`

### Link Account to Application:

After callback, link the Gmail account using the tokens received:

```bash
curl -X POST http://localhost:8000/api/v1/auth/gmail/link \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-access-token>" \
  -d '{
    "access_token": "<gmail-access-token>",
    "refresh_token": "<gmail-refresh-token>",
    "gmail_email": "your-gmail@gmail.com",
    "expires_at": "2024-12-31T10:00:00"
  }'
```

## Step 6: Fetch Emails

Once account is linked, fetch emails:

```python
from worker.tasks.email_processor import fetch_and_process_emails

# Run task (in production, use Celery)
result = fetch_and_process_emails(
    user_id="<user-id>",
    email_account_id="<email-account-id>",
    max_results=5
)

print(result)
# Output: {
#   "status": "success",
#   "emails_fetched": 5,
#   "emails_processed": 5,
#   "errors": []
# }
```

## Token Lifecycle

### Initial Authorization

1. User grants permission → receives access token (expires in ~1 hour)
2. Also receives refresh token (long-lived, doesn't expire)
3. Both are encrypted with Fernet AES-256 and stored in database

### Token Expiration & Refresh

1. Application checks token expiration before each Gmail API call
2. If expired, automatically refreshes using refresh token
3. Stores new access token and updates expiration time

### Token Revocation

1. If refresh token fails, user needs to re-authorize
2. User can revoke access in Google Account Settings
3. Application will receive error on next API call

## Scopes

The application requests the following Gmail scope:

- `https://www.googleapis.com/auth/gmail.modify` - Full access to Gmail (read, write, delete)

This allows:

- Reading emails
- Marking as read/unread
- Applying labels
- Archiving emails
- Sending emails
- Drafts

### More Restrictive Scopes (if needed)

- `https://www.googleapis.com/auth/gmail.readonly` - Read-only access
- `https://www.googleapis.com/auth/gmail.labels` - Label management only

To change scopes, modify `GmailConnector.scopes` in `backend/connectors/gmail.py`

## Troubleshooting

### "Invalid Client ID" Error

- Verify `GMAIL_CLIENT_ID` is copied correctly (should end with `.apps.googleusercontent.com`)
- Check it's from the correct Google Cloud Project
- Ensure project has Gmail API enabled

### "Redirect URI mismatch" Error

- The redirect URI in your code must **exactly match** what's registered in Google Console
- Including protocol (`http://` vs `https://`)
- Case-sensitive
- No trailing slashes

### "Access token expired" Error

- This is expected! Application should automatically refresh using refresh token
- If refresh fails, token may be revoked, user needs to re-authorize

### "Can't access Gmail" Error

- Check that `https://www.googleapis.com/auth/gmail.modify` scope is granted
- User may have revoked access - ask them to re-authorize
- Check token encryption key is correct

### "Invalid Encryption Key" Error

- Ensure `ENCRYPTION_KEY` environment variable is set
- Use the Fernet key format from the Python code above
- Don't modify encrypted tokens manually

## Security Considerations

1. **Token Storage**: Tokens are encrypted at rest using Fernet (AES-256)
2. **Token Transmission**: Always use HTTPS in production (not HTTP)
3. **Token Scope**: Limited to Gmail access only
4. **Token Refresh**: Old tokens are overwritten when refreshed
5. **No Token Logging**: Tokens are never logged or displayed in debug output

## API Endpoints

### Start OAuth Flow

```
POST /api/v1/auth/gmail/authorize
Authorization: Bearer <jwt-token>
Body: {}
Response: { "authorization_url": "https://..." }
```

### OAuth Callback (called by Google)

```
GET /api/v1/auth/gmail/callback?code=...&state=...
Response: { "access_token": "...", "refresh_token": "...", ... }
```

### Link Account

```
POST /api/v1/auth/gmail/link
Authorization: Bearer <jwt-token>
Body: {
  "access_token": "...",
  "refresh_token": "...",
  "gmail_email": "user@gmail.com",
  "expires_at": "2024-12-31T10:00:00"
}
Response: { "email_account_id": "...", ... }
```

### Fetch Emails

```
POST /api/v1/jobs/email/fetch (future endpoint)
Authorization: Bearer <jwt-token>
Body: { "email_account_id": "..." }
Response: { "status": "success", "emails_fetched": 5, ... }
```

## Next Steps

1. Test OAuth flow with real Gmail account
2. Implement email classification with LLM
3. Implement auto-reply rules
4. Add email management endpoints
5. Build frontend UI for Gmail connection

## References

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Documentation](https://developers.google.com/gmail/api/guides)
- [Gmail API Scopes](https://developers.google.com/gmail/api/auth/scopes)
- [google-auth-oauthlib Library](https://github.com/googleapis/google-auth-library-python-oauthlib)
