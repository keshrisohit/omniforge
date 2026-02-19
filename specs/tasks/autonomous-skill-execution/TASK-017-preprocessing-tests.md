# TASK-017: Unit tests for preprocessing pipeline

**Priority:** P0 (Must Have)
**Estimated Effort:** Medium (1-3 days)
**Dependencies:** TASK-002, TASK-003, TASK-009

---

## Description

Create comprehensive unit tests for the preprocessing pipeline components: `StringSubstitutor`, `ContextLoader`, and `DynamicInjector`. Target 95% code coverage for these components. Tests should cover normal operations, edge cases, error handling, and security scenarios.

## Files to Create

- `tests/skills/test_string_substitutor.py`
- `tests/skills/test_context_loader.py`
- `tests/skills/test_dynamic_injector.py`

## Test Requirements

### StringSubstitutor Tests

```python
class TestStringSubstitutor:
    """Unit tests for StringSubstitutor."""

    # Basic substitution tests
    def test_substitute_arguments(self):
        """$ARGUMENTS should be replaced with arguments value."""

    def test_substitute_skill_dir(self):
        """${SKILL_DIR} should be replaced with skill directory path."""

    def test_substitute_session_id(self):
        """${CLAUDE_SESSION_ID} should be replaced with session ID."""

    def test_substitute_workspace(self):
        """${WORKSPACE} should be replaced with working directory."""

    def test_substitute_user(self):
        """${USER} should be replaced with current user."""

    def test_substitute_date(self):
        """${DATE} should be replaced with current date."""

    # Edge cases
    def test_substitute_multiple_occurrences(self):
        """Multiple occurrences of same variable should all be replaced."""

    def test_substitute_mixed_syntax(self):
        """Both $VAR and ${VAR} syntax should work."""

    def test_auto_append_arguments_when_missing(self):
        """Arguments should be appended if not in content."""

    def test_no_auto_append_when_arguments_present(self):
        """Arguments should not be appended if already in content."""

    def test_undefined_variable_warning(self, caplog):
        """Undefined variables should log warning but not fail."""

    def test_custom_variables(self):
        """Custom variables should be substituted."""

    def test_empty_arguments(self):
        """Empty arguments should not cause issues."""

    def test_build_context_generates_session_id(self):
        """build_context should generate session ID if not provided."""
```

### ContextLoader Tests

```python
class TestContextLoader:
    """Unit tests for ContextLoader."""

    # File reference extraction
    def test_extract_see_pattern(self):
        """Should extract 'See reference.md for details' pattern."""

    def test_extract_read_pattern(self):
        """Should extract 'Read examples.md for usage' pattern."""

    def test_extract_dash_pattern(self):
        """Should extract '- reference.md: Description' pattern."""

    def test_extract_bold_pattern(self):
        """Should extract '**reference.md**: Description' pattern."""

    def test_extract_line_count_hint(self):
        """Should parse '(1,200 lines)' hints."""

    def test_extract_nested_path(self):
        """Should handle 'templates/report.md' paths."""

    # File validation
    def test_validate_existing_files(self, tmp_path):
        """Only existing files should be included in available_files."""

    def test_ignore_missing_files(self, tmp_path):
        """Missing referenced files should be silently ignored."""

    # Context loading
    def test_load_initial_context(self, tmp_path):
        """load_initial_context should return LoadedContext."""

    def test_line_count_calculation(self):
        """Line count should be calculated correctly."""

    # Tracking
    def test_mark_file_loaded(self):
        """mark_file_loaded should track loaded files."""

    def test_get_loaded_files(self):
        """get_loaded_files should return copy of loaded files set."""

    # Prompt building
    def test_build_available_files_prompt(self):
        """Should format available files for system prompt."""

    def test_build_available_files_prompt_empty(self):
        """Empty available_files should return empty string."""
```

### DynamicInjector Tests

```python
class TestDynamicInjector:
    """Unit tests for DynamicInjector."""

    # Command extraction
    def test_extract_injection_pattern(self):
        """Should find !`command` patterns in content."""

    def test_extract_multiple_injections(self):
        """Should find all injection patterns."""

    def test_duplicate_commands_processed_once(self):
        """Duplicate commands should only execute once."""

    # Command execution
    async def test_process_replaces_commands(self):
        """Should replace !`command` with output."""

    async def test_process_preserves_non_injection_content(self):
        """Non-injection content should be preserved."""

    async def test_process_handles_failed_commands(self):
        """Failed commands should show error in content."""

    async def test_process_timeout_protection(self):
        """Commands exceeding timeout should fail gracefully."""

    async def test_process_output_truncation(self):
        """Large output should be truncated."""

    # Security validation
    def test_blocks_shell_semicolon(self):
        """Should block commands with semicolon."""

    def test_blocks_shell_and(self):
        """Should block commands with &&."""

    def test_blocks_shell_or(self):
        """Should block commands with ||."""

    def test_blocks_shell_pipe(self):
        """Should block commands with |."""

    def test_blocks_shell_redirect(self):
        """Should block commands with > or <."""

    def test_blocks_command_substitution(self):
        """Should block $() and backtick substitution."""

    def test_blocks_path_traversal(self):
        """Should block commands with path traversal."""

    def test_blocks_absolute_path(self):
        """Should block commands starting with /."""

    def test_allowed_tools_whitelist(self):
        """Should only allow whitelisted commands."""

    def test_allowed_tools_pattern_matching(self):
        """Bash(gh:*) should allow gh commands."""

    def test_no_restrictions_warning(self, caplog):
        """No allowed_tools should log security warning."""

    # Edge cases
    async def test_empty_content(self):
        """Empty content should return empty content."""

    async def test_no_injections(self):
        """Content without injections should pass through unchanged."""
```

## Coverage Targets

| Component | Target Coverage |
|-----------|-----------------|
| StringSubstitutor | 95% |
| ContextLoader | 95% |
| DynamicInjector | 90% (async complicates some paths) |

## Acceptance Criteria

- [ ] All listed tests implemented
- [ ] Tests pass reliably (no flakiness)
- [ ] Coverage targets met
- [ ] Security scenarios thoroughly tested
- [ ] Edge cases covered
- [ ] Tests run in under 30 seconds
- [ ] Tests are independent (no shared state)

## Testing Commands

```bash
# Run preprocessing tests
pytest tests/skills/test_string_substitutor.py -v
pytest tests/skills/test_context_loader.py -v
pytest tests/skills/test_dynamic_injector.py -v

# Run with coverage
pytest tests/skills/test_*.py --cov=src/omniforge/skills --cov-report=term-missing
```

## Technical Notes

- Use `pytest.fixture` for common test setup
- Use `tmp_path` fixture for file system tests
- Use `AsyncMock` for async method mocking
- Use `caplog` fixture for log assertions
- Security tests are critical - don't skip any
- Consider property-based testing with hypothesis for edge cases
