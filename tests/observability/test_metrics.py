"""Tests for Prometheus metrics collection."""

from omniforge.observability.metrics import (
    agent_executions_total,
    get_metrics_collector,
    skill_execution_duration_seconds,
    skill_executions_total,
)


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_get_metrics_collector_returns_singleton(self) -> None:
        """get_metrics_collector should return same instance each time."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2

    def test_record_agent_execution_increments_counter(self) -> None:
        """record_agent_execution should increment counter with correct labels."""
        collector = get_metrics_collector()

        # Get initial value
        before = agent_executions_total.labels(status="success", agent_id="test-agent-1")._value._value  # type: ignore[attr-defined]

        # Record execution
        collector.record_agent_execution(status="success", agent_id="test-agent-1")

        # Check counter incremented
        after = agent_executions_total.labels(status="success", agent_id="test-agent-1")._value._value  # type: ignore[attr-defined]
        assert after == before + 1

    def test_record_agent_execution_with_no_agent_id(self) -> None:
        """record_agent_execution should use 'unknown' when agent_id is None."""
        collector = get_metrics_collector()

        # Get initial value
        before = agent_executions_total.labels(status="failed", agent_id="unknown")._value._value  # type: ignore[attr-defined]

        # Record execution without agent_id
        collector.record_agent_execution(status="failed", agent_id=None)

        # Check counter incremented
        after = agent_executions_total.labels(status="failed", agent_id="unknown")._value._value  # type: ignore[attr-defined]
        assert after == before + 1

    def test_record_skill_execution_increments_counter(self) -> None:
        """record_skill_execution should increment counter with correct labels."""
        collector = get_metrics_collector()

        # Get initial value
        before = skill_executions_total.labels(
            skill_id="skill-1", skill_name="processor", status="success"
        )._value._value  # type: ignore[attr-defined]

        # Record execution
        collector.record_skill_execution(
            skill_id="skill-1",
            skill_name="processor",
            duration_seconds=1.5,
            status="success",
        )

        # Check counter incremented
        after = skill_executions_total.labels(
            skill_id="skill-1", skill_name="processor", status="success"
        )._value._value  # type: ignore[attr-defined]
        assert after == before + 1

    def test_record_skill_execution_records_histogram(self) -> None:
        """record_skill_execution should record duration in histogram."""
        collector = get_metrics_collector()

        # Record execution
        collector.record_skill_execution(
            skill_id="skill-2",
            skill_name="analyzer",
            duration_seconds=2.5,
            status="success",
        )

        # Check histogram has sample
        histogram = skill_execution_duration_seconds.labels(
            skill_id="skill-2", skill_name="analyzer", status="success"
        )
        assert histogram._sum._value > 0  # type: ignore[attr-defined]

    def test_generate_metrics_returns_bytes(self) -> None:
        """generate_metrics should return metrics in Prometheus format."""
        collector = get_metrics_collector()

        # Record some metrics
        collector.record_agent_execution(status="success", agent_id="test-1")
        collector.record_skill_execution(
            skill_id="skill-1",
            skill_name="test",
            duration_seconds=1.0,
            status="success",
        )

        # Generate metrics
        metrics_data = collector.generate_metrics()

        # Check format
        assert isinstance(metrics_data, bytes)
        assert b"agent_executions_total" in metrics_data
        assert b"skill_execution_duration_seconds" in metrics_data

    def test_record_http_request_records_metrics(self) -> None:
        """record_http_request should record both counter and histogram."""
        collector = get_metrics_collector()

        # Record request
        collector.record_http_request(
            method="GET",
            endpoint="/api/agents",
            status_code=200,
            duration_seconds=0.05,
        )

        # Generate metrics to verify
        metrics_data = collector.generate_metrics()
        assert b"http_requests_total" in metrics_data
        assert b"http_request_duration_seconds" in metrics_data
