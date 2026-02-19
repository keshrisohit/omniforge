# TASK-002: Create StringSubstitutor for variable replacement

**Priority:** P1 (Should Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** None

---

## Description

Create `StringSubstitutor` class to replace variables in skill content before LLM execution. Supports standard variables ($ARGUMENTS, ${SKILL_DIR}, ${SESSION_ID}, etc.) and auto-appends arguments if not present in content.

This component is part of the preprocessing pipeline: ContextLoader -> DynamicInjector -> **StringSubstitutor** -> Execution

## Files to Create

- `src/omniforge/skills/string_substitutor.py` - StringSubstitutor implementation

## Implementation Requirements

### Supported Variables
| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking skill |
| `${CLAUDE_SESSION_ID}` | Unique session identifier |
| `${SKILL_DIR}` | Absolute path to skill directory |
| `${WORKSPACE}` | Current working directory |
| `${USER}` | Current user name |
| `${DATE}` | Current date (YYYY-MM-DD) |

### SubstitutionContext dataclass
- `arguments: str` - User-provided arguments
- `session_id: str` - Unique session ID
- `skill_dir: str` - Absolute path to skill directory
- `workspace: str` - Working directory
- `user: str` - Current user name
- `date: str` - Current date
- `custom_vars: dict[str, str]` - Additional custom variables

### SubstitutedContent dataclass
- `content: str` - Content with variables replaced
- `substitutions_made: int` - Count of substitutions
- `undefined_vars: list[str]` - Undefined variables found

### StringSubstitutor class
- `substitute(content, context, auto_append_arguments=True)` - Main method
- `build_context(arguments, session_id, skill_dir, ...)` - Build context with defaults
- Auto-append `ARGUMENTS: {value}` if $ARGUMENTS not in content
- Log warning for undefined variables (don't fail)

## Acceptance Criteria

- [ ] All standard variables substituted correctly
- [ ] Handles both `$VAR` and `${VAR}` syntax
- [ ] Auto-appends arguments when not present in content
- [ ] Logs warning for undefined variables
- [ ] Custom variables support via context
- [ ] Session ID auto-generated if not provided
- [ ] Unit tests achieve 95% coverage
- [ ] Type hints pass mypy

## Testing

```python
def test_substitute_arguments():
    substitutor = StringSubstitutor()
    context = SubstitutionContext(arguments="data.csv")
    result = substitutor.substitute("Process: $ARGUMENTS", context)
    assert result.content == "Process: data.csv"
    assert result.substitutions_made == 1

def test_auto_append_arguments():
    context = SubstitutionContext(arguments="test.txt")
    result = substitutor.substitute("Process file", context)
    assert "ARGUMENTS: test.txt" in result.content

def test_undefined_variable_warning():
    result = substitutor.substitute("${UNDEFINED_VAR}", context)
    assert "UNDEFINED_VAR" in result.undefined_vars
```

## Technical Notes

- Use regex for variable detection: `\$\{?([A-Z][A-Z0-9_]*)\}?`
- Order of replacement matters (longer patterns first)
- Generate session ID: `session-{date}-{uuid[:8]}`
- Use `os.getcwd()` for workspace default
- Use `os.environ.get("USER")` for user default
