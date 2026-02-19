"""OAuth callback route handlers.

This module provides OAuth callback endpoints for integration providers
like Notion, Slack, etc. Handles the OAuth redirect flow after user authorization.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

# Create router for OAuth callbacks (no prefix - uses /oauth directly)
router = APIRouter(tags=["oauth"])


@router.get("/oauth/callback/notion")
async def notion_oauth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
) -> RedirectResponse:
    """Handle OAuth callback from Notion.

    This endpoint is called by Notion after user authorizes the integration.
    It exchanges the authorization code for access tokens, stores them securely,
    and redirects the user back to the conversation flow.

    Args:
        code: OAuth authorization code from Notion
        state: OAuth state parameter (contains session_id for CSRF protection)

    Returns:
        RedirectResponse to frontend conversation page with session_id

    Raises:
        HTTPException: If code/state invalid or token exchange fails

    Examples:
        >>> # Notion redirects to:
        >>> GET /oauth/callback/notion?code=abc123&state=session-id
        >>>
        >>> # Redirects to:
        >>> https://app.omniforge.ai/builder/conversation?session={session_id}&success=true
    """
    # TODO: Implement OAuth token exchange
    # 1. Validate state parameter
    # 2. Exchange code for access token via Notion API
    # 3. Store encrypted credentials in database
    # 4. Extract session_id from state

    # For now, simulate successful OAuth
    session_id = state  # In production, extract from signed state

    # Redirect back to frontend conversation
    frontend_url = f"http://localhost:3000/builder/conversation?session={session_id}&integration=notion&success=true"

    return RedirectResponse(url=frontend_url)


@router.get("/oauth/callback/slack")
async def slack_oauth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
) -> RedirectResponse:
    """Handle OAuth callback from Slack.

    This endpoint is called by Slack after user authorizes the integration.
    It exchanges the authorization code for access tokens, stores them securely,
    and redirects the user back to the conversation flow.

    Args:
        code: OAuth authorization code from Slack
        state: OAuth state parameter (contains session_id for CSRF protection)

    Returns:
        RedirectResponse to frontend conversation page with session_id

    Raises:
        HTTPException: If code/state invalid or token exchange fails

    Examples:
        >>> # Slack redirects to:
        >>> GET /oauth/callback/slack?code=xyz789&state=session-id
        >>>
        >>> # Redirects to:
        >>> https://app.omniforge.ai/builder/conversation?session={session_id}&success=true
    """
    # TODO: Implement Slack OAuth token exchange
    session_id = state

    frontend_url = f"http://localhost:3000/builder/conversation?session={session_id}&integration=slack&success=true"

    return RedirectResponse(url=frontend_url)


@router.get("/oauth/authorize/{integration}")
async def initiate_oauth(
    integration: str,
    session: str = Query(..., description="Conversation session ID"),
) -> RedirectResponse:
    """Initiate OAuth flow for an integration provider.

    Generates OAuth authorization URL with proper scope and state, then
    redirects user to the provider's authorization page.

    Args:
        integration: Integration type (notion, slack, etc.)
        session: Conversation session ID (used in state parameter)

    Returns:
        RedirectResponse to provider's OAuth authorization page

    Raises:
        HTTPException: If integration type not supported

    Examples:
        >>> GET /oauth/authorize/notion?session=session-123
        >>>
        >>> # Redirects to:
        >>> https://api.notion.com/v1/oauth/authorize?client_id=...&state=...
    """
    # OAuth configuration (should come from environment variables)
    oauth_configs = {
        "notion": {
            "authorize_url": "https://api.notion.com/v1/oauth/authorize",
            "client_id": "notion_client_id",  # TODO: Load from env
            "redirect_uri": "http://localhost:8000/oauth/callback/notion",
            "scope": "read_content write_content",
        },
        "slack": {
            "authorize_url": "https://slack.com/oauth/v2/authorize",
            "client_id": "slack_client_id",  # TODO: Load from env
            "redirect_uri": "http://localhost:8000/oauth/callback/slack",
            "scope": "channels:read channels:write chat:write",
        },
    }

    if integration not in oauth_configs:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported integration: {integration}",
        )

    config = oauth_configs[integration]

    # Build authorization URL
    # TODO: Sign state parameter for security
    auth_url = (
        f"{config['authorize_url']}"
        f"?client_id={config['client_id']}"
        f"&redirect_uri={config['redirect_uri']}"
        f"&response_type=code"
        f"&state={session}"
        f"&scope={config['scope']}"
    )

    return RedirectResponse(url=auth_url)
