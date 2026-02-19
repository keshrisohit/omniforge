# Selective Truncation for Tool Results

## Overview

The tool system supports **selective truncation** of results to optimize context window usage while preserving important metadata. This is particularly useful for tools that return large lists of items (e.g., file matches, search results, database records).

## How It Works

### The Problem

Tools like `GlobTool` and `GrepTool` can return hundreds or thousands of matching items. When these results are stored in the conversation context, they can quickly consume the available context window, leaving less room for actual conversation and reasoning.

### The Solution

Rather than truncating the entire result or keeping all results, we use **selective truncation**:

1. **Identify truncatable fields**: Mark specific fields (like `matches`) as safe to truncate
2. **Preserve metadata**: Keep important metadata like counts, patterns, and configuration
3. **Truncate only large lists**: Only truncate list fields that exceed the size threshold
4. **Add truncation notes**: Indicate what was truncated and how much

## Usage

### For Tool Developers

When creating a tool that returns large result lists, mark truncatable fields in the `ToolResult`:

```python
from omniforge.tools.base import ToolResult

# Return result with truncatable_fields specified
return ToolResult(
    success=True,
    result={
        "matches": large_list_of_matches,  # Will be truncated
        "match_count": len(large_list_of_matches),  # Always preserved
        "pattern": search_pattern,  # Always preserved
        "base_path": base_path,  # Always preserved
    },
    duration_ms=duration_ms,
    truncatable_fields=["matches"],  # Only truncate 'matches'
)
```

### For Tool Users

Use the `truncate_for_context()` method to selectively truncate results:

```python
# Execute a tool
result = await glob_tool.execute(arguments, context)

# Truncate for context (keeps first 10 items by default)
truncated_result = result.truncate_for_context(max_items=10)

# Or with custom message
truncated_result = result.truncate_for_context(
    max_items=5,
    truncation_message="Results limited for display"
)
```

## Example

### Before Truncation

```python
{
    "success": True,
    "result": {
        "matches": [  # 1000 items
            {"path": "/path/to/file1.py", "name": "file1.py", ...},
            {"path": "/path/to/file2.py", "name": "file2.py", ...},
            # ... 998 more items ...
        ],
        "match_count": 1000,
        "pattern": "**/*.py",
        "base_path": "/src"
    }
}
```

### After Truncation (max_items=5)

```python
{
    "success": True,
    "result": {
        "matches": [  # Only 5 items
            {"path": "/path/to/file1.py", "name": "file1.py", ...},
            {"path": "/path/to/file2.py", "name": "file2.py", ...},
            {"path": "/path/to/file3.py", "name": "file3.py", ...},
            {"path": "/path/to/file4.py", "name": "file4.py", ...},
            {"path": "/path/to/file5.py", "name": "file5.py", ...}
        ],
        "match_count": 1000,  # Preserved!
        "pattern": "**/*.py",  # Preserved!
        "base_path": "/src",  # Preserved!
        "matches_truncation_note": "Showing 5 of 1000 items"
    }
}
```

## Built-in Tools with Truncation

The following built-in tools support selective truncation:

- **GlobTool**: Truncates `matches` while preserving `match_count`, `pattern`, `base_path`, `truncated`
- **GrepTool**: Truncates `matches` while preserving `match_count`, `pattern`, `file_path`, `truncated`

## API Reference

### `ToolResult.truncate_for_context()`

```python
def truncate_for_context(
    self,
    max_items: int = 10,
    truncation_message: Optional[str] = None
) -> ToolResult:
    """Truncate result to save context window space.

    Args:
        max_items: Maximum items to keep in truncatable fields (default: 10)
        truncation_message: Custom message to add when truncating (optional)

    Returns:
        New ToolResult with truncated data
    """
```

### `truncatable_fields`

A list of field names in the result dictionary that can be safely truncated:

```python
truncatable_fields: list[str] = Field(
    default_factory=list,
    description="Fields that can be truncated to save context (others preserved)"
)
```

## Benefits

1. **Context Efficiency**: Save context window space by limiting large lists
2. **Metadata Preservation**: Keep important information like counts and patterns
3. **Transparency**: Users see truncation notes indicating what was limited
4. **Flexibility**: Tool developers choose what to truncate, users choose how much
5. **Backward Compatible**: Works seamlessly with existing tools (no truncation if not specified)

## Best Practices

1. **Mark large lists as truncatable**: Any field that could return dozens or hundreds of items
2. **Preserve counts and metadata**: Always keep summary information that helps users understand the full scope
3. **Use descriptive truncation notes**: Help users understand what was truncated
4. **Set reasonable defaults**: Default `max_items` to balance context usage and usefulness (typically 10-20)
5. **Document truncation behavior**: Let users know which fields may be truncated

## See Also

- [Tool Development Guide](./development.md)
- [Context Management](../context/management.md)
- [Tool Best Practices](./best-practices.md)
