# Observability and Monitoring

OmniForge provides comprehensive observability features for monitoring, debugging, and performance analysis in production environments.

## Features

- **Structured Logging** - JSON-formatted logs with correlation IDs for distributed tracing
- **Prometheus Metrics** - Production-ready metrics for monitoring agent and skill execution
- **Execution Tracing** - Detailed traces with per-skill timing and data flow
- **Health Checks** - Endpoint for monitoring system health and dependencies

## Structured Logging

### Configuration

Configure logging via environment variables:

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
export LOG_LEVEL=INFO

# Enable JSON logs for production (default: true)
export JSON_LOGS=true
```

### Log Format

All logs include:
- `timestamp` - ISO 8601 format
- `level` - Log level (info, error, warning, etc.)
- `event` - Structured event name
- `correlation_id` - Request correlation ID for tracing
- Additional context fields

Example JSON log:

```json
{
  "timestamp": "2026-01-26T10:30:45.123456",
  "level": "info",
  "event": "agent_execution_started",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "agent-123",
  "trace_id": "trace-456",
  "skill_count": 3
}
```

### Correlation IDs

Every HTTP request automatically receives a correlation ID that propagates through:
- All log messages during request processing
- HTTP response headers (`X-Correlation-ID`)
- Execution traces

This enables end-to-end request tracing across distributed systems.

## Prometheus Metrics

### Metrics Endpoint

Access metrics at:

```
GET /metrics
```

Response format: Prometheus exposition format (text/plain)

### Available Metrics

#### Agent Execution Metrics

**`agent_executions_total`** (Counter)
- Total number of agent executions
- Labels: `status` (success, failed, timeout), `agent_id`

```prometheus
agent_executions_total{status="success",agent_id="agent-123"} 42
agent_executions_total{status="failed",agent_id="agent-123"} 2
```

#### Skill Execution Metrics

**`skill_executions_total`** (Counter)
- Total number of skill executions
- Labels: `skill_id`, `skill_name`, `status`

```prometheus
skill_executions_total{skill_id="skill-1",skill_name="processor",status="success"} 150
```

**`skill_execution_duration_seconds`** (Histogram)
- Skill execution duration in seconds
- Labels: `skill_id`, `skill_name`, `status`
- Buckets: 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0 seconds

```prometheus
skill_execution_duration_seconds_bucket{skill_id="skill-1",skill_name="processor",status="success",le="1.0"} 120
skill_execution_duration_seconds_sum{skill_id="skill-1",skill_name="processor",status="success"} 45.6
skill_execution_duration_seconds_count{skill_id="skill-1",skill_name="processor",status="success"} 150
```

#### HTTP Request Metrics

**`http_requests_total`** (Counter)
- Total number of HTTP requests
- Labels: `method`, `endpoint`, `status_code`

**`http_request_duration_seconds`** (Histogram)
- HTTP request duration in seconds
- Labels: `method`, `endpoint`
- Buckets: 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0 seconds

### Prometheus Configuration

Add OmniForge to your Prometheus configuration:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'omniforge'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboards

Example queries for Grafana:

**Agent Execution Rate**
```promql
rate(agent_executions_total[5m])
```

**Skill Execution Success Rate**
```promql
rate(skill_executions_total{status="success"}[5m]) /
rate(skill_executions_total[5m])
```

**95th Percentile Skill Duration**
```promql
histogram_quantile(0.95,
  rate(skill_execution_duration_seconds_bucket[5m])
)
```

**HTTP Error Rate**
```promql
rate(http_requests_total{status_code=~"5.."}[5m])
```

## Execution Tracing

### Overview

Execution traces provide detailed visibility into agent runs, including:
- Per-skill execution timing
- Input/output data flow
- Error information
- Retry attempts

### Trace Structure

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "agent-123",
  "status": "success",
  "started_at": "2026-01-26T10:30:45.123Z",
  "completed_at": "2026-01-26T10:30:48.456Z",
  "total_duration_ms": 3333,
  "skill_count": 3,
  "successful_skills": 3,
  "failed_skills": 0,
  "skills": [
    {
      "skill_id": "skill-1",
      "skill_name": "data_processor",
      "started_at": "2026-01-26T10:30:45.123Z",
      "completed_at": "2026-01-26T10:30:46.234Z",
      "duration_ms": 1111,
      "status": "success",
      "input_size_bytes": 256,
      "output_size_bytes": 512,
      "error": null
    }
  ]
}
```

### Accessing Traces

Traces are automatically created for each agent execution and can be:
- Logged at completion (structured log event)
- Retrieved via API (future enhancement)
- Stored in distributed tracing systems (future enhancement)

## Health Checks

### Health Check Endpoint

Monitor system health:

```
GET /health
```

### Response Format

**Healthy (200 OK)**
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "scheduler": {
      "status": "healthy",
      "message": "Scheduler running normally"
    },
    "llm": {
      "status": "healthy",
      "message": "LLM provider available"
    }
  },
  "version": "0.1.0"
}
```

**Unhealthy (503 Service Unavailable)**
```json
{
  "status": "unhealthy",
  "components": {
    "database": {
      "status": "unhealthy",
      "message": "Database error: connection refused"
    },
    "scheduler": {
      "status": "healthy",
      "message": "Scheduler running normally"
    },
    "llm": {
      "status": "healthy",
      "message": "LLM provider available"
    }
  },
  "version": "0.1.0"
}
```

**Degraded (200 OK)**
```json
{
  "status": "degraded",
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "scheduler": {
      "status": "healthy",
      "message": "Scheduler running normally"
    },
    "llm": {
      "status": "degraded",
      "message": "LLM provider error: rate limit exceeded"
    }
  },
  "version": "0.1.0"
}
```

### Health Check Components

1. **Database** - Verifies database connectivity with simple query
2. **Scheduler** - Checks if agent scheduler is running
3. **LLM** - Validates LLM provider availability

### Load Balancer Integration

Configure your load balancer to use the health check endpoint:

**Example: AWS ALB Target Group**
```
Health check path: /health
Healthy threshold: 2
Unhealthy threshold: 3
Timeout: 5 seconds
Interval: 30 seconds
Success codes: 200
```

**Example: Kubernetes Liveness/Readiness**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Alerting

### Recommended Alerts

**High Agent Failure Rate**
```promql
rate(agent_executions_total{status="failed"}[5m]) /
rate(agent_executions_total[5m]) > 0.1
```
Alert when >10% of agent executions fail

**Slow Skill Execution**
```promql
histogram_quantile(0.95,
  rate(skill_execution_duration_seconds_bucket[5m])
) > 30
```
Alert when 95th percentile skill duration exceeds 30 seconds

**Service Unhealthy**
```
GET /health returns 503
```
Alert when health check fails

**High HTTP Error Rate**
```promql
rate(http_requests_total{status_code=~"5.."}[5m]) > 10
```
Alert when >10 HTTP 5xx errors per second

## Best Practices

### Development

1. Use console logging format for local development:
   ```bash
   export JSON_LOGS=false
   export LOG_LEVEL=DEBUG
   ```

2. Test health checks locally:
   ```bash
   curl http://localhost:8000/health
   ```

3. Monitor metrics during development:
   ```bash
   curl http://localhost:8000/metrics
   ```

### Production

1. **Always use JSON logs** for structured log aggregation:
   ```bash
   export JSON_LOGS=true
   export LOG_LEVEL=INFO
   ```

2. **Configure log aggregation** (ELK, Splunk, CloudWatch):
   - Index by correlation_id for request tracing
   - Set up alerts on error logs
   - Create dashboards for key events

3. **Set up Prometheus** scraping:
   - 15-30 second scrape interval
   - Configure alerting rules
   - Create Grafana dashboards

4. **Monitor health checks**:
   - Configure load balancer health checks
   - Set up alerting on health check failures
   - Monitor individual component health

5. **Retention policies**:
   - Logs: 30-90 days
   - Metrics: 30-365 days (depending on resolution)
   - Traces: 7-30 days

### Security

1. **Never log sensitive data**:
   - API keys, tokens, passwords
   - User PII (unless required and compliant)
   - Full request/response bodies with credentials

2. **Protect metrics endpoint**:
   - Consider authentication for production
   - Limit to internal network access
   - Monitor for abuse

3. **Sanitize error messages**:
   - Avoid exposing internal paths
   - Don't include stack traces in production logs
   - Redact sensitive information from errors

## Troubleshooting

### High Memory Usage

Check Prometheus metrics retention:
```python
# Metrics are stored in memory by prometheus_client
# Consider using a Prometheus pushgateway for long-term storage
```

### Missing Correlation IDs

Ensure requests include `X-Correlation-ID` header or let middleware generate them:
```bash
curl -H "X-Correlation-ID: my-trace-id" http://localhost:8000/api/agents
```

### Health Check Failing

1. Check individual component status in response body
2. Review application logs for errors
3. Verify database connectivity
4. Confirm scheduler is running

### Logs Not Appearing

1. Verify LOG_LEVEL is set correctly
2. Check JSON_LOGS configuration
3. Ensure structured logging is initialized
4. Review log aggregation configuration

## Future Enhancements

Planned observability features:

1. **OpenTelemetry Integration** - Standard distributed tracing
2. **Trace Storage** - Persistent trace storage and retrieval API
3. **Custom Metrics** - User-defined metrics from agent code
4. **Log Sampling** - Reduce log volume in high-traffic scenarios
5. **APM Integration** - DataDog, New Relic, etc.
6. **Distributed Tracing** - Cross-service trace propagation
