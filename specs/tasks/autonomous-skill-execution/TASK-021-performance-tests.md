# TASK-021: Performance tests and benchmarks

**Priority:** P2 (Nice to Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** TASK-019

---

## Description

Create performance tests and benchmarks to validate that autonomous skill execution meets performance targets. Measure iteration overhead, token savings from progressive context loading, and concurrent execution capacity.

## Files to Create

- `tests/skills/test_performance.py`
- `benchmarks/autonomous_execution_benchmarks.py`

## Performance Targets (from Technical Plan)

| Metric | Target |
|--------|--------|
| Iteration overhead | <500ms per iteration |
| Simple task completion | <10s total |
| Token savings | 40% reduction from progressive loading |
| Concurrent executions | 100+ per worker |

## Test Requirements

### Iteration Overhead Tests

```python
class TestIterationOverhead:
    """Tests for ReAct loop iteration overhead."""

    @pytest.mark.performance
    async def test_iteration_overhead_under_500ms(self, executor, mock_llm):
        """Single iteration should complete in under 500ms (excluding LLM)."""
        # Mock LLM to return instantly
        mock_llm.call.return_value = instant_response

        start = time.perf_counter()
        # Run single iteration
        duration_ms = (time.perf_counter() - start) * 1000

        assert duration_ms < 500, f"Iteration took {duration_ms}ms, expected <500ms"

    @pytest.mark.performance
    async def test_preprocessing_overhead_minimal(self, executor):
        """Preprocessing should add minimal overhead."""
        start = time.perf_counter()

        await executor._preprocess_content(
            user_request="test",
            session_id="test-session",
            task_id="test",
        )

        duration_ms = (time.perf_counter() - start) * 1000
        assert duration_ms < 100, f"Preprocessing took {duration_ms}ms"

    @pytest.mark.performance
    async def test_event_emission_overhead_minimal(self, executor):
        """Event emission should not block execution."""
        events = []
        start = time.perf_counter()

        async for event in executor.execute("test"):
            events.append(event)

        # Event collection overhead
        duration_ms = (time.perf_counter() - start) * 1000
        overhead_per_event = duration_ms / len(events)

        assert overhead_per_event < 10, f"Event overhead: {overhead_per_event}ms per event"
```

### Token Savings Tests

```python
class TestTokenSavings:
    """Tests for progressive context loading token savings."""

    @pytest.mark.performance
    def test_initial_context_under_limit(self, context_loader, large_skill):
        """Initial context should be limited to SKILL.md only."""
        context = context_loader.load_initial_context()

        # SKILL.md is under 500 lines
        assert context.line_count <= 500

        # Calculate approximate tokens (1 line ~ 10 tokens)
        estimated_tokens = context.line_count * 10
        assert estimated_tokens < 5000  # Much less than full skill

    @pytest.mark.performance
    def test_token_savings_measurement(self, skill_with_supporting_files):
        """Measure token savings from progressive loading."""
        # Calculate tokens if all files loaded upfront
        total_lines = sum(
            len(f.read_text().splitlines())
            for f in skill_with_supporting_files.iterdir()
            if f.suffix in ['.md', '.txt']
        )
        total_tokens_upfront = total_lines * 10

        # Calculate tokens with progressive loading (SKILL.md only)
        skill_md = skill_with_supporting_files / "SKILL.md"
        progressive_tokens = len(skill_md.read_text().splitlines()) * 10

        savings_pct = (1 - progressive_tokens / total_tokens_upfront) * 100

        assert savings_pct >= 40, f"Token savings: {savings_pct}%, expected >=40%"
```

### Concurrent Execution Tests

```python
class TestConcurrentExecution:
    """Tests for concurrent skill execution capacity."""

    @pytest.mark.performance
    @pytest.mark.slow
    async def test_concurrent_executions(self, orchestrator, mock_llm):
        """Should support 100+ concurrent executions."""
        num_concurrent = 100

        async def execute_skill(i):
            events = []
            async for event in orchestrator.execute(
                "test-skill",
                f"Task {i}",
                task_id=f"task-{i}",
            ):
                events.append(event)
            return events

        # Execute all concurrently
        start = time.perf_counter()
        results = await asyncio.gather(*[
            execute_skill(i) for i in range(num_concurrent)
        ])
        duration = time.perf_counter() - start

        # All should complete successfully
        assert all(len(r) > 0 for r in results)

        # Log performance
        print(f"Completed {num_concurrent} executions in {duration:.2f}s")
        print(f"Throughput: {num_concurrent / duration:.2f} executions/second")

    @pytest.mark.performance
    async def test_memory_stable_under_load(self, orchestrator, mock_llm):
        """Memory should not grow unbounded during concurrent execution."""
        import tracemalloc

        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]

        # Run many executions
        for _ in range(50):
            async for _ in orchestrator.execute("test-skill", "task"):
                pass

        final_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        memory_growth = final_memory - initial_memory
        memory_growth_mb = memory_growth / (1024 * 1024)

        assert memory_growth_mb < 100, f"Memory grew by {memory_growth_mb}MB"
```

### Benchmarks

```python
# benchmarks/autonomous_execution_benchmarks.py

import asyncio
import time
from statistics import mean, stdev

async def benchmark_iteration_overhead():
    """Benchmark single iteration overhead."""
    executor = create_test_executor(mock_llm=True)

    times = []
    for _ in range(100):
        start = time.perf_counter()
        # Single iteration
        times.append((time.perf_counter() - start) * 1000)

    print(f"Iteration overhead:")
    print(f"  Mean: {mean(times):.2f}ms")
    print(f"  Std:  {stdev(times):.2f}ms")
    print(f"  Min:  {min(times):.2f}ms")
    print(f"  Max:  {max(times):.2f}ms")

async def benchmark_preprocessing():
    """Benchmark preprocessing pipeline."""
    # Similar benchmarking for preprocessing

async def benchmark_concurrent_scaling():
    """Benchmark scaling with concurrent executions."""
    for num_concurrent in [10, 50, 100, 200]:
        start = time.perf_counter()
        # Run num_concurrent executions
        duration = time.perf_counter() - start
        throughput = num_concurrent / duration
        print(f"  {num_concurrent} concurrent: {throughput:.2f} exec/s")

if __name__ == "__main__":
    asyncio.run(benchmark_iteration_overhead())
    asyncio.run(benchmark_preprocessing())
    asyncio.run(benchmark_concurrent_scaling())
```

## Acceptance Criteria

- [ ] Iteration overhead measured and validated (<500ms)
- [ ] Token savings measured and validated (>=40%)
- [ ] Concurrent execution capacity validated (100+)
- [ ] Memory stability under load verified
- [ ] Benchmark scripts created for ongoing monitoring
- [ ] Performance regression tests in CI (optional)

## Testing Commands

```bash
# Run performance tests
pytest tests/skills/test_performance.py -v -m performance

# Run benchmarks
python benchmarks/autonomous_execution_benchmarks.py

# Run with profiling
pytest tests/skills/test_performance.py --profile
```

## Technical Notes

- Use `pytest.mark.performance` to isolate performance tests
- Use `pytest.mark.slow` for long-running tests
- Mock LLM calls to measure framework overhead only
- Consider using `pytest-benchmark` for detailed benchmarking
- Run benchmarks on consistent hardware for reliable comparisons
- Memory testing requires `tracemalloc` module
