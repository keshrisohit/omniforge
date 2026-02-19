# TASK-404: Implement External API Tool Base Class

## Description

Create a base class for external API tools that provides common HTTP functionality. This enables easy creation of tools for weather APIs, search engines, and other external services.

## Requirements

- Create `ExternalAPITool` class extending BaseTool:
  - Constructor accepting:
    - name: str
    - description: str
    - base_url: str
    - headers: Optional[dict]
    - timeout_ms: int = 30000
  - Use httpx for async HTTP requests
  - Implement common HTTP methods:
    - `_get(path, params)` async method
    - `_post(path, json_data)` async method
    - `_request(method, path, **kwargs)` internal method
  - Implement `definition` property (override in subclasses)
  - Implement `execute()` to be overridden by specific tools
  - Include request/response logging for debugging
  - Handle HTTP errors as ToolResult errors
- Create example `WeatherAPITool` as reference implementation:
  - Wraps a mock weather API
  - Demonstrates parameter handling
  - Shows response parsing

## Acceptance Criteria

- [ ] HTTP GET/POST methods work correctly
- [ ] Timeout enforced on HTTP calls
- [ ] Headers passed to all requests
- [ ] HTTP errors converted to ToolResult errors
- [ ] Subclasses can easily implement specific APIs
- [ ] WeatherAPITool example demonstrates pattern
- [ ] Unit tests with mocked HTTP responses

## Dependencies

- TASK-102 (for BaseTool, ToolDefinition)
- External: httpx (already in project)

## Files to Create/Modify

- `src/omniforge/tools/builtin/external.py` (new)
- `tests/tools/builtin/test_external.py` (new)

## Estimated Complexity

Medium (4-5 hours)

## Key Considerations

- Use httpx async client for non-blocking I/O
- Consider connection pooling for repeated calls
- API key handling should be secure
