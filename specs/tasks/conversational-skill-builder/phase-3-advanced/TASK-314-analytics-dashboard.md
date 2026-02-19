# TASK-314: Analytics and Usage Dashboard

**Phase**: 3B (B2B2C Enterprise)
**Estimated Effort**: 12 hours
**Dependencies**: TASK-311 (Multi-Tenant Isolation)
**Priority**: P2

## Objective

Create analytics and usage dashboard for Tier 2 customers to monitor agent performance across their end customers.

## Requirements

- Create aggregated usage metrics (executions, success rate, latency)
- Implement per-customer breakdown of agent usage
- Create time-series analytics (daily, weekly, monthly trends)
- Add cost tracking and estimation
- Create exportable reports (CSV, PDF)
- Implement anomaly detection for usage spikes

## Implementation Notes

- Aggregate agent_executions table for metrics
- Store pre-computed aggregates for dashboard performance
- Real-time metrics via Prometheus, historical via database
- Cost estimation based on LLM token usage
- Anomaly detection: >2 std dev from rolling average

## Acceptance Criteria

- [ ] Dashboard shows total executions, success rate, avg latency
- [ ] Per-customer breakdown available with drill-down
- [ ] Time-series charts show trends over time
- [ ] Cost tracking estimates LLM and compute costs
- [ ] Reports exportable in CSV and PDF formats
- [ ] Anomaly alerts for unusual usage patterns
- [ ] Dashboard loads in < 2 seconds for 10K executions
- [ ] API documentation for analytics endpoints

## Files to Create/Modify

- `src/omniforge/b2b2c/analytics/__init__.py` - Analytics package
- `src/omniforge/b2b2c/analytics/aggregator.py` - Metric aggregation
- `src/omniforge/b2b2c/analytics/timeseries.py` - Time-series analytics
- `src/omniforge/b2b2c/analytics/cost.py` - Cost tracking
- `src/omniforge/b2b2c/analytics/reports.py` - Report generation
- `src/omniforge/b2b2c/analytics/anomaly.py` - Anomaly detection
- `src/omniforge/api/routes/analytics.py` - Analytics API endpoints
- `tests/b2b2c/analytics/test_aggregator.py` - Aggregation tests
- `tests/b2b2c/analytics/test_reports.py` - Report generation tests
