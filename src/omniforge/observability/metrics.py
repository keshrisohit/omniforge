"""Prometheus metrics collection for monitoring.

This module provides Prometheus metrics for tracking agent executions,
skill performance, and system health.
"""

from typing import Optional

from prometheus_client import Counter, Histogram, generate_latest

# Agent execution metrics
agent_executions_total = Counter(
    "agent_executions_total",
    "Total number of agent executions",
    labelnames=["status", "agent_id"],
)

# Skill execution metrics
skill_execution_duration_seconds = Histogram(
    "skill_execution_duration_seconds",
    "Skill execution duration in seconds",
    labelnames=["skill_id", "skill_name", "status"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

skill_executions_total = Counter(
    "skill_executions_total",
    "Total number of skill executions",
    labelnames=["skill_id", "skill_name", "status"],
)

# HTTP request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    labelnames=["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)


class MetricsCollector:
    """Collects and exposes Prometheus metrics.

    Provides methods for recording agent executions, skill performance,
    and HTTP requests.
    """

    def record_agent_execution(self, status: str, agent_id: Optional[str] = None) -> None:
        """Record an agent execution event.

        Args:
            status: Execution status (success, failed, timeout)
            agent_id: Optional agent identifier

        Example:
            >>> collector = get_metrics_collector()
            >>> collector.record_agent_execution("success", "agent-123")
        """
        agent_executions_total.labels(status=status, agent_id=agent_id or "unknown").inc()

    def record_skill_execution(
        self,
        skill_id: str,
        skill_name: str,
        duration_seconds: float,
        status: str,
    ) -> None:
        """Record a skill execution event.

        Args:
            skill_id: Skill identifier
            skill_name: Human-readable skill name
            duration_seconds: Execution duration in seconds
            status: Execution status (success, failed, timeout)

        Example:
            >>> collector = get_metrics_collector()
            >>> collector.record_skill_execution(
            ...     skill_id="skill-1",
            ...     skill_name="data_processor",
            ...     duration_seconds=1.5,
            ...     status="success"
            ... )
        """
        skill_executions_total.labels(
            skill_id=skill_id,
            skill_name=skill_name,
            status=status,
        ).inc()

        skill_execution_duration_seconds.labels(
            skill_id=skill_id,
            skill_name=skill_name,
            status=status,
        ).observe(duration_seconds)

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record an HTTP request event.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Request endpoint path
            status_code: HTTP status code
            duration_seconds: Request duration in seconds

        Example:
            >>> collector = get_metrics_collector()
            >>> collector.record_http_request("GET", "/api/agents", 200, 0.05)
        """
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration_seconds)

    def generate_metrics(self) -> bytes:
        """Generate Prometheus metrics in text format.

        Returns:
            Metrics in Prometheus exposition format

        Example:
            >>> collector = get_metrics_collector()
            >>> metrics_text = collector.generate_metrics()
            >>> print(metrics_text.decode('utf-8'))
        """
        return generate_latest()


# Singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global MetricsCollector instance.

    Returns:
        Singleton MetricsCollector instance

    Example:
        >>> collector = get_metrics_collector()
        >>> collector.record_agent_execution("success")
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
