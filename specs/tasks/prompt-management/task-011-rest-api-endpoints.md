# TASK-011: Implement REST API Endpoints

## Objective

Create FastAPI routes for prompt management operations including CRUD, versioning, composition, and experiments.

## Requirements

### API Routes (`src/omniforge/api/routes/prompts.py`)

**Request/Response Models**:
- `PromptCreateRequest`: layer, name, content, scope_id, description, merge_points, variables_schema
- `PromptUpdateRequest`: content, change_message, merge_points, variables_schema
- `PromptComposeRequest`: agent_id, feature_ids, user_input, variables, skip_cache
- `PromptRollbackRequest`: to_version
- `ExperimentCreateRequest`: name, description, success_metric, variants
- `PromptResponse`, `PromptVersionResponse`, `ComposedPromptResponse`

**Prompt CRUD Endpoints**:
- `GET /api/v1/prompts` - List prompts (filter by layer, tenant)
- `POST /api/v1/prompts` - Create prompt
- `GET /api/v1/prompts/{id}` - Get prompt
- `PUT /api/v1/prompts/{id}` - Update prompt
- `DELETE /api/v1/prompts/{id}` - Soft delete prompt

**Versioning Endpoints**:
- `GET /api/v1/prompts/{id}/versions` - List versions
- `GET /api/v1/prompts/{id}/versions/{version_number}` - Get specific version
- `POST /api/v1/prompts/{id}/rollback` - Rollback to version

**Composition Endpoints**:
- `POST /api/v1/prompts/compose` - Compose prompt for agent
- `POST /api/v1/prompts/preview` - Preview without caching
- `POST /api/v1/prompts/validate` - Validate template syntax

**Experiment Endpoints**:
- `POST /api/v1/prompts/{id}/experiments` - Create experiment
- `GET /api/v1/prompts/{id}/experiments` - List experiments
- `GET /api/v1/experiments/{id}` - Get experiment
- `PUT /api/v1/experiments/{id}` - Update experiment
- `POST /api/v1/experiments/{id}/start` - Start experiment
- `POST /api/v1/experiments/{id}/stop` - Stop experiment
- `POST /api/v1/experiments/{id}/promote` - Promote variant

**Cache Endpoints** (admin only):
- `DELETE /api/v1/prompts/cache` - Clear cache
- `GET /api/v1/prompts/cache/stats` - Cache statistics

### Error Handling
- Convert PromptError subclasses to appropriate HTTP responses
- Include error code and message in response body

### Authentication/Authorization
- All endpoints require authentication
- Use dependency injection for current user/tenant context
- Check RBAC permissions before operations

## Acceptance Criteria
- [ ] All endpoints implemented and return correct status codes
- [ ] Request validation via Pydantic models
- [ ] Error responses follow consistent format
- [ ] Tenant context properly extracted and used
- [ ] Permission checks integrated (placeholder ok for now)
- [ ] API documented with OpenAPI/Swagger
- [ ] Integration tests cover main flows
- [ ] Tests verify error responses

## Dependencies
- TASK-010 (SDK PromptManager)
- TASK-009 (ExperimentManager)

## Estimated Complexity
Complex
