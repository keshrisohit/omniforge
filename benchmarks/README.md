# OmniForge Performance Benchmarks

This directory contains performance benchmarks for OmniForge autonomous skill execution.

## Overview

The benchmark suite measures and validates key performance metrics:

- **Iteration Overhead**: Time per ReAct loop iteration (excluding LLM calls)
- **Preprocessing Pipeline**: Time for content preprocessing and substitution
- **Token Savings**: Reduction in tokens from progressive context loading
- **Concurrent Execution**: Throughput and scaling with concurrent executions

## Running Benchmarks

### Run All Benchmarks

```bash
python benchmarks/autonomous_execution_benchmarks.py
```

This will run all benchmarks and generate a comprehensive performance report.

### Run Specific Benchmarks

```python
from benchmarks.autonomous_execution_benchmarks import benchmark_iteration_overhead
import asyncio

asyncio.run(benchmark_iteration_overhead())
```

Available benchmark functions:
- `benchmark_iteration_overhead()`
- `benchmark_preprocessing()`
- `benchmark_concurrent_scaling()`
- `benchmark_token_savings()`

## Performance Targets

| Metric | Target | Description |
|--------|--------|-------------|
| Iteration overhead | <500ms | Time per ReAct iteration (excluding LLM) |
| Preprocessing overhead | <100ms | Time for content preprocessing |
| Token savings | >=40% | Reduction from progressive loading vs upfront |
| Concurrent execution | 100+ | Number of concurrent executions supported |

## Performance Tests

Performance tests are located in `tests/skills/test_performance.py` and can be run with:

```bash
# Run all performance tests
pytest tests/skills/test_performance.py -v -m performance

# Run all tests including slow tests
pytest tests/skills/test_performance.py -v -m "performance or slow"

# Run without the slow concurrent execution tests
pytest tests/skills/test_performance.py -v -m "performance and not slow"
```

## Test Markers

Performance tests use pytest markers for organization:

- `@pytest.mark.performance`: Marks tests as performance tests
- `@pytest.mark.slow`: Marks long-running tests (>5 seconds)

## Interpreting Results

### Iteration Overhead

Measures the framework overhead per ReAct loop iteration. Low overhead (<500ms) ensures that:
- The framework doesn't add significant latency beyond LLM calls
- Skills can complete simple tasks quickly (<10s total)
- Users get responsive execution

### Token Savings

Validates that progressive context loading reduces token usage by loading only `SKILL.md` initially, with supporting files loaded on-demand. Benefits:
- Reduced cost (fewer tokens per execution)
- Faster initial LLM calls (smaller prompts)
- Better context window utilization

### Concurrent Execution

Tests system capacity for handling multiple concurrent skill executions. Important for:
- Platform scalability
- Multi-user support
- Parallel skill orchestration

### Memory Stability

Verifies that repeated executions don't cause memory leaks. Ensures:
- Stable long-running deployments
- No resource exhaustion over time
- Predictable memory usage

## Continuous Monitoring

These benchmarks should be run:

1. **Before releases** - To validate performance targets
2. **After major changes** - To detect performance regressions
3. **Periodically** - To track performance trends over time

Consider adding these to CI/CD for automated performance regression detection.

## Contributing

When adding new performance tests or benchmarks:

1. Follow existing patterns for consistency
2. Use `@pytest.mark.performance` for performance tests
3. Use `@pytest.mark.slow` for tests taking >5 seconds
4. Document performance targets and rationale
5. Ensure benchmarks are reproducible and deterministic
