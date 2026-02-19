# TASK-006: Security (RBAC Extensions + Context Sanitizer)

**Phase**: 4 - Integration
**Complexity**: Simple
**Dependencies**: TASK-004
**Files to create/modify**:
- Modify `src/omniforge/security/rbac.py` (add permissions, update role mappings)
- Create `src/omniforge/orchestration/sanitizer.py`
- Create `tests/orchestration/test_sanitizer.py`

## Description

Extend existing RBAC with orchestration permissions and create a regex-based context sanitizer for safe inter-agent context passing.

### RBAC Extensions (modify existing `src/omniforge/security/rbac.py`)

Add to existing `Permission` enum:
- `ORCHESTRATION_DELEGATE = "orchestration:delegate"`
- `HANDOFF_INITIATE = "handoff:initiate"`
- `HANDOFF_CANCEL = "handoff:cancel"`

Update `ROLE_PERMISSIONS` dict:
- `END_USER`: add HANDOFF_INITIATE (users can trigger handoffs)
- `OPERATOR`: add ORCHESTRATION_DELEGATE, HANDOFF_INITIATE, HANDOFF_CANCEL
- `DEVELOPER`: add ORCHESTRATION_DELEGATE, HANDOFF_INITIATE, HANDOFF_CANCEL
- `ADMIN`: add ORCHESTRATION_DELEGATE, HANDOFF_INITIATE, HANDOFF_CANCEL

### Context Sanitizer (`src/omniforge/orchestration/sanitizer.py`)

`ContextSanitizer` class with regex-based PII redaction.

Patterns to redact:
- Email addresses -> `[EMAIL]`
- 16-digit card numbers -> `[CARD]`
- Password/secret/token key-value pairs -> `[REDACTED]`

**Methods:**
- `sanitize(text: str) -> str` - Apply all patterns
- `add_pattern(pattern: str, replacement: str)` - Add custom pattern at runtime
- `is_clean(text: str) -> bool` - Returns True if text contains no sensitive patterns

Compile regex patterns once at init time for performance.

## Acceptance Criteria

- New permissions exist in `Permission` enum
- `check_permission(Role.OPERATOR, Permission.HANDOFF_INITIATE)` returns True
- `check_permission(Role.VIEWER, Permission.HANDOFF_INITIATE)` returns False
- `check_permission(Role.END_USER, Permission.HANDOFF_INITIATE)` returns True
- Existing permissions and role mappings are unchanged
- Sanitizer redacts emails, card numbers, and password/token patterns
- Sanitizer leaves clean text unchanged
- Custom patterns can be added and work correctly
- `is_clean` returns correct boolean
