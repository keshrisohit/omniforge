# TASK-104: Notion OAuth Integration

**Phase**: 1 (MVP)
**Estimated Effort**: 12 hours
**Dependencies**: TASK-101
**Priority**: P0

## Objective

Implement OAuth 2.0 integration for Notion, including credential encryption, token refresh, and workspace discovery. This is the first integration and establishes the pattern for future OAuth providers.

## Requirements

- Create `OAuthConfig` model for integration configuration
- Create `OAuthManager` class with `initiate_flow()`, `complete_flow()`, `get_access_token()` methods
- Implement Fernet encryption for token storage (per technical plan Section 9.3)
- Implement automatic token refresh when expired
- Create Notion-specific OAuth provider with workspace discovery
- Store OAuth state for callback validation
- Support multiple credentials per user (different Notion workspaces)

## Implementation Notes

- Reference technical plan Section 9.1 and 9.2 for OAuth flow and manager specification
- Notion OAuth URL: `https://api.notion.com/v1/oauth/authorize`
- Notion Token URL: `https://api.notion.com/v1/oauth/token`
- Encryption key from `CREDENTIAL_ENCRYPTION_KEY` environment variable
- State includes user_id, tenant_id, session_id for callback routing
- 90%+ test coverage required for OAuth token handling (per review)

## Acceptance Criteria

- [ ] `OAuthManager.initiate_flow()` returns valid Notion authorize URL with state
- [ ] `OAuthManager.complete_flow()` exchanges code for tokens and stores encrypted
- [ ] `OAuthManager.get_access_token()` returns decrypted token, refreshes if expired
- [ ] State validation prevents CSRF attacks on callback
- [ ] User+tenant ownership check prevents unauthorized credential access
- [ ] Notion workspace name stored after successful OAuth
- [ ] Mock OAuth tests cover token exchange and refresh edge cases
- [ ] 90%+ test coverage for token handling

## Files to Create/Modify

- `src/omniforge/integrations/__init__.py` - Integrations package init
- `src/omniforge/integrations/oauth/__init__.py` - OAuth package init
- `src/omniforge/integrations/oauth/manager.py` - OAuthManager, OAuthConfig
- `src/omniforge/integrations/oauth/providers/__init__.py` - Providers package
- `src/omniforge/integrations/oauth/providers/notion.py` - NotionOAuthProvider
- `src/omniforge/integrations/credentials/__init__.py` - Credentials package
- `src/omniforge/integrations/credentials/encryption.py` - CredentialEncryption class
- `tests/integrations/__init__.py` - Test package
- `tests/integrations/oauth/test_manager.py` - OAuth manager tests
- `tests/integrations/oauth/test_notion_provider.py` - Notion-specific tests
