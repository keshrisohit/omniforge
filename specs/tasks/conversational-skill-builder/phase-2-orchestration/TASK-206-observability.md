# TASK-206: Observability and Monitoring

**Phase**: 2 (Multi-Skill)
**Estimated Effort**: 10 hours
**Dependencies**: TASK-201 (Sequential Orchestration), TASK-202 (APScheduler)
**Priority**: P1

## Objective

Add operational observability with structured logging, basic metrics, and execution tracing. This addresses review warning about operational observability.

## Requirements

- Implement structured logging with correlation IDs for request tracing
- Add Prometheus metrics: agent_executions_total, skill_execution_duration_seconds
- Create execution trace with per-skill timing and status
- Add health check endpoint for scheduler status
- Implement log aggregation ready format (JSON structured logs)
- Create dashboard-ready metrics for execution success rate

## Implementation Notes

- Per review: operational observability is important for production readiness
- Use Python logging with StructLog for structured output
- Prometheus client for metrics (already in tech stack)
- Correlation ID propagated through all async calls
- Health check verifies: database, scheduler, LLM connectivity

## Acceptance Criteria

- [ ] All log messages include correlation_id for tracing
- [ ] Prometheus metrics exposed at /metrics endpoint
- [ ] agent_executions_total counter tracks by status (success/failure)
- [ ] skill_execution_duration_seconds histogram tracks per-skill timing
- [ ] Health check endpoint at /health returns scheduler status
- [ ] Logs output as JSON for log aggregation
- [ ] Execution trace shows skill-by-skill timing breakdown
- [ ] Documentation for metrics and their meanings

## Files to Create/Modify

- `src/omniforge/observability/__init__.py` - Observability package
- `src/omniforge/observability/logging.py` - Structured logging setup
- `src/omniforge/observability/metrics.py` - Prometheus metrics
- `src/omniforge/observability/tracing.py` - Execution tracing
- `src/omniforge/api/routes/health.py` - Health check endpoint
- `src/omniforge/api/middleware/correlation.py` - Correlation ID middleware
- `src/omniforge/execution/orchestration/engine.py` - Add metric instrumentation
- `tests/observability/test_metrics.py` - Metrics tests
- `docs/observability.md` - Observability documentation
