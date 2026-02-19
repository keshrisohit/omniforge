# TASK-108: Integration Tests and Quality Verification

**Phase**: 1 (MVP)
**Estimated Effort**: 12 hours
**Dependencies**: TASK-106
**Priority**: P0

## Objective

Create comprehensive integration tests that verify the full end-to-end flow of agent creation, OAuth integration, and execution. Ensure 80% overall test coverage and validate all critical paths.

## Requirements

- Create end-to-end test for conversation flow (discovery -> generation -> activation)
- Create integration tests for OAuth flow with mock Notion API
- Create integration tests for agent execution via API
- Add performance test for conversation response latency (< 3 seconds)
- Add database migration tests (SQLite and PostgreSQL)
- Generate test coverage report and verify 80% minimum

## Implementation Notes

- Use pytest-asyncio for async tests
- Use testcontainers for PostgreSQL integration tests
- Mock external APIs (Notion, LLM) with responses library
- Reference technical plan Section 15 for testing strategy
- Focus on critical paths identified in review: state transitions, frontmatter validation, OAuth token handling

## Acceptance Criteria

- [ ] E2E test: Full conversation from start to agent activation
- [ ] E2E test: OAuth flow with mock Notion returns valid credentials
- [ ] E2E test: Agent execution returns expected result
- [ ] Performance test: Conversation response < 3 seconds
- [ ] Database test: Migrations work on both SQLite and PostgreSQL
- [ ] Coverage report shows 80%+ overall coverage
- [ ] All critical paths identified in review have dedicated tests
- [ ] CI pipeline runs all integration tests successfully

## Files to Create/Modify

- `tests/integration/__init__.py` - Integration test package
- `tests/integration/test_conversation_e2e.py` - Full conversation flow tests
- `tests/integration/test_oauth_flow.py` - OAuth integration tests
- `tests/integration/test_agent_execution.py` - Execution tests
- `tests/integration/test_database_migrations.py` - Migration tests
- `tests/performance/__init__.py` - Performance test package
- `tests/performance/test_response_latency.py` - Latency tests
- `tests/conftest.py` - Shared fixtures (extend existing)
- `.github/workflows/test.yml` - CI configuration (extend if exists)
